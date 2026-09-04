import React, { useState, useEffect } from 'react';
import {
  ConfigProvider, Layout, Menu, Table, Card, Button, Modal, Form, Input,
  InputNumber, Tag, Space, message, Popconfirm, Breadcrumb, Row, Col,
  Tooltip, Empty, theme, Statistic, Typography
} from 'antd';
import {
  ClusterOutlined, PlusOutlined, DeleteOutlined,
  EditOutlined, ReloadOutlined, CheckCircleOutlined, SyncOutlined,
  AppstoreOutlined, GlobalOutlined, LockOutlined
} from '@ant-design/icons';
import * as k8sApi from './api/k8sApi';

const { Header, Content, Sider, Footer } = Layout;
const { Title, Text } = Typography;


const PALETTE = {
  primary: '#3b82f6',
  accent: '#22d3ee',
  violet: '#a78bfa',
  green: '#34d399',
  red: '#f87171',
  textDim: 'rgba(148, 163, 184, 0.9)',
};

const spaceTheme = {
  algorithm: theme.darkAlgorithm,
  token: {
    colorPrimary: PALETTE.primary,
    colorInfo: PALETTE.accent,
    colorBgBase: '#05070f',
    colorBgContainer: '#0c1226',
    colorBgElevated: '#101830',
    colorBorder: 'rgba(99, 130, 246, 0.35)',
    colorBorderSecondary: 'rgba(99, 130, 246, 0.18)',
    borderRadius: 10,
    fontSize: 14,
  },
  components: {
    Layout: { headerBg: 'transparent', siderBg: 'transparent', bodyBg: 'transparent' },
    Menu: {
      itemBg: 'transparent',
      itemColor: PALETTE.textDim,
      itemHoverBg: 'rgba(59, 130, 246, 0.10)',
      itemHoverColor: '#dbeafe',
      itemSelectedBg: 'rgba(59, 130, 246, 0.22)',
      itemSelectedColor: '#93c5fd',
      itemMarginInline: 8,
      itemBorderRadius: 8,
    },
    Table: {
      headerBg: 'rgba(59, 130, 246, 0.14)',
      headerColor: '#93c5fd',
      rowHoverBg: 'rgba(59, 130, 246, 0.07)',
      headerBorderRadius: 10,
    },
    Card: { colorBgContainer: 'rgba(12, 18, 38, 0.72)' },
    Modal: { contentBg: '#0c1226', headerBg: '#0c1226' },
  },
};

const GLOBAL_CSS = `
  html, body { background: #05070f; }

  .k8s-shell {
    min-height: 100vh;
    background:
      radial-gradient(1000px 500px at 15% -10%, rgba(59, 130, 246, 0.18), transparent 60%),
      radial-gradient(900px 500px at 90% 0%, rgba(167, 139, 250, 0.12), transparent 55%),
      linear-gradient(180deg, #0a0f22 0%, #070b18 45%, #05070f 100%);
    background-attachment: fixed;
  }

  /* ✨ Animated starfield */
  .starfield {
    position: fixed;
    inset: 0;
    z-index: 0;
    pointer-events: none;
    background-image:
      radial-gradient(1.5px 1.5px at 12% 22%, rgba(255,255,255,.95) 50%, transparent 51%),
      radial-gradient(1px 1px at 27% 68%, rgba(255,255,255,.7) 50%, transparent 51%),
      radial-gradient(2px 2px at 41% 13%, rgba(147,197,253,.9) 50%, transparent 51%),
      radial-gradient(1px 1px at 55% 82%, rgba(255,255,255,.6) 50%, transparent 51%),
      radial-gradient(1.5px 1.5px at 64% 34%, rgba(34,211,238,.85) 50%, transparent 51%),
      radial-gradient(1px 1px at 76% 57%, rgba(255,255,255,.75) 50%, transparent 51%),
      radial-gradient(2px 2px at 88% 18%, rgba(167,139,250,.8) 50%, transparent 51%),
      radial-gradient(1px 1px at 93% 74%, rgba(255,255,255,.65) 50%, transparent 51%),
      radial-gradient(1px 1px at 6% 88%, rgba(255,255,255,.6) 50%, transparent 51%),
      radial-gradient(1.5px 1.5px at 33% 45%, rgba(255,255,255,.8) 50%, transparent 51%);
    background-size: 620px 620px;
    animation: twinkle 6s ease-in-out infinite alternate;
  }
  @keyframes twinkle {
    from { opacity: 0.35; }
    to   { opacity: 0.85; }
  }

  /* 🌈 Gradient headline text */
  .gradient-text {
    background: linear-gradient(92deg, #60a5fa 0%, #22d3ee 55%, #a78bfa 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  /* 🪟 Frosted glass cards */
  .glass-card.ant-card {
    background: rgba(12, 18, 38, 0.72);
    border: 1px solid rgba(99, 130, 246, 0.20);
    backdrop-filter: blur(10px);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
    transition: border-color 0.3s ease, box-shadow 0.3s ease, transform 0.3s ease;
  }
  .glass-card.ant-card:hover {
    border-color: rgba(99, 130, 246, 0.45);
    box-shadow: 0 12px 36px rgba(59, 130, 246, 0.18);
  }
  .stat-card.ant-card:hover { transform: translateY(-3px); }

  /* 🛰️ Clusters sidebar */
  .cluster-sider {
    position: sticky;
    top: 64px;
    height: calc(100vh - 64px);
    background: rgba(9, 14, 30, 0.55) !important;
    backdrop-filter: blur(12px);
    border-right: 1px solid rgba(99, 130, 246, 0.16);
    z-index: 5;
  }
  .cluster-sider .ant-layout-sider-children {
    display: flex;
    flex-direction: column;
    height: 100%;
  }
  /* Allow two-line cluster items (name + address) */
  .cluster-sider .ant-menu-item {
    height: auto !important;
    min-height: 54px;
    padding-top: 8px;
    padding-bottom: 8px;
    line-height: 1.35;
    white-space: normal;
  }

  ::-webkit-scrollbar { width: 8px; height: 8px; }
  ::-webkit-scrollbar-thumb { background: rgba(59, 130, 246, 0.35); border-radius: 8px; }
  ::-webkit-scrollbar-track { background: transparent; }
`;

/* Extracts a readable message from an API error, falling back to a default. */
const getErrorMessage = (err, fallback) =>
  err?.response?.data?.message || err?.message || fallback;

const phaseEmoji = (phase) => {
  switch (phase) {
    case 'Running': return '🟢';
    case 'Pending': return '🟡';
    case 'Succeeded': return '✔️';
    case 'Failed':
    case 'Error':
    case 'CrashLoopBackOff': return '🔴';
    default: return '⚪';
  }
};

export default function App() {
  const [clusters, setClusters] = useState([]);
  const [namespaces, setNamespaces] = useState([]);
  const [apps, setApps] = useState([]);

  const [selectedCluster, setSelectedCluster] = useState(null);
  const [selectedNamespace, setSelectedNamespace] = useState(null);
  const [loading, setLoading] = useState(false);

  const [isClusterModalOpen, setIsClusterModalOpen] = useState(false);
  const [isNsModalOpen, setIsNsModalOpen] = useState(false);
  const [isAppModalOpen, setIsAppModalOpen] = useState(false);
  const [editingApp, setEditingApp] = useState(null);

  const [clusterForm] = Form.useForm();
  const [namespaceForm] = Form.useForm();
  const [appForm] = Form.useForm();

  /* ─────────── 📡 Data fetching ─────────── */

  const fetchClusters = async () => {
    setLoading(true);
    try {
      const res = await k8sApi.getClusters();
      setClusters(res.data);
    } catch (err) {
      message.error(getErrorMessage(err, 'Failed to load clusters'));
    } finally {
      setLoading(false);
    }
  };

  /* On first load: fetch clusters and auto-select the first one,
     so namespaces & apps are visible immediately. */
  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const res = await k8sApi.getClusters();
        if (cancelled) return;
        setClusters(res.data);
        if (res.data?.length) {
          const first = res.data[0];
          setSelectedCluster(first);
          const nsRes = await k8sApi.getNamespaces(first.id);
          if (cancelled) return;
          setNamespaces(nsRes.data);
        }
      } catch (err) {
        if (!cancelled) message.error(getErrorMessage(err, 'Failed to load clusters'));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const fetchNamespaces = async (clusterId) => {
    setLoading(true);
    try {
      const res = await k8sApi.getNamespaces(clusterId);
      setNamespaces(res.data);
      setApps([]);
      setSelectedNamespace(null);
    } catch (err) {
      message.error(getErrorMessage(err, 'Failed to load namespaces'));
    } finally {
      setLoading(false);
    }
  };

  const fetchApps = async (namespaceId) => {
    setLoading(true);
    try {
      const res = await k8sApi.getApps(namespaceId);
      setApps(res.data);
    } catch (err) {
      message.error(getErrorMessage(err, 'Failed to load apps'));
    } finally {
      setLoading(false);
    }
  };

  /* ─────────── ⚡ Actions ─────────── */

  const handleCreateCluster = async (values) => {
    try {
      await k8sApi.createCluster(values);
      message.success('Cluster created successfully');
      setIsClusterModalOpen(false);
      clusterForm.resetFields();
      fetchClusters();
    } catch (err) {
      message.error(getErrorMessage(err, 'Failed to create cluster'));
    }
  };

  const handleCreateNamespace = async (values) => {
    try {
      await k8sApi.createNamespace({ ...values, cluster_id: selectedCluster.id });
      message.success('Namespace created successfully');
      setIsNsModalOpen(false);
      namespaceForm.resetFields();
      fetchNamespaces(selectedCluster.id);
    } catch (err) {
      message.error(getErrorMessage(err, 'Failed to create namespace'));
    }
  };

  const handleDeleteNamespace = async (id) => {
    try {
      await k8sApi.deleteNamespace(id);
      message.success('Namespace deleted');
      fetchNamespaces(selectedCluster.id);
    } catch (err) {
      message.error(getErrorMessage(err, 'Failed to delete namespace'));
    }
  };

  const handleCreateOrUpdateApp = async (values) => {
    try {
      if (editingApp) {
        await k8sApi.updateApp(editingApp.id, values);
        message.success('App updated successfully');
      } else {
        await k8sApi.createApp({ ...values, namespace: selectedNamespace.id });
        message.success('App created successfully');
      }
      setIsAppModalOpen(false);
      setEditingApp(null);
      appForm.resetFields();
      fetchApps(selectedNamespace.id);
    } catch (err) {
      message.error(getErrorMessage(err, 'Failed to save app'));
    }
  };

  const handleDeleteApp = async (id) => {
    try {
      await k8sApi.deleteApp(id);
      message.success('App deleted');
      fetchApps(selectedNamespace.id);
    } catch (err) {
      message.error(getErrorMessage(err, 'Failed to delete app'));
    }
  };

  /* ─────────── 🚪 Modal helpers ─────────── */

  const openClusterModal = () => {
    clusterForm.resetFields();
    setIsClusterModalOpen(true);
  };

  const openNsModal = () => {
    namespaceForm.resetFields();
    setIsNsModalOpen(true);
  };

  const openCreateAppModal = () => {
    setEditingApp(null);
    appForm.resetFields();
    setIsAppModalOpen(true);
  };

  const openEditAppModal = (record) => {
    setEditingApp(record);
    appForm.setFieldsValue(record);
    setIsAppModalOpen(true);
  };

  /* ─────────── 📊 Stats ─────────── */

  const stats = [
    { emoji: '🌌', label: 'Clusters', value: clusters.length, color: '#60a5fa' },
    { emoji: '🗂️', label: 'Namespaces', value: namespaces.length, color: PALETTE.accent },
    { emoji: '🛰️', label: 'Apps', value: apps.length, color: PALETTE.violet },
    { emoji: '⚙️', label: 'Total Replicas', value: apps.reduce((s, a) => s + (a.replicas || 0), 0), color: PALETTE.green },
  ];

  /* ─────────── 🌌 Cluster sidebar items ─────────── */

  const clusterItems = clusters.map((c) => ({
    key: String(c.id),
    icon: <span style={{ fontSize: 16 }}>🛰️</span>,
    label: (
      <Tooltip title={c.address} placement="right">
        <div style={{ minWidth: 0 }}>
          <div style={{
            fontWeight: selectedCluster?.id === c.id ? 700 : 500,
            color: selectedCluster?.id === c.id ? '#bfdbfe' : 'inherit',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {c.name}
          </div>
          <div style={{
            fontSize: 11,
            color: 'rgba(148, 163, 184, 0.65)',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            🌐 {c.address}
          </div>
        </div>
      </Tooltip>
    ),
    onClick: () => {
      setSelectedCluster(c);
      fetchNamespaces(c.id);
    },
  }));

  /* ─────────── 📋 App table columns ─────────── */

  const appColumns = [
    {
      title: '🚀 App', dataIndex: 'name', key: 'name',
      render: (name) => <Text strong style={{ color: '#e2e8f0' }}>{name}</Text>,
    },
    {
      title: '📦 Image', dataIndex: 'image', key: 'image',
      render: (img) => <Text code style={{ color: PALETTE.accent }}>{img}</Text>,
    },
    { title: '🔢 Replicas', dataIndex: 'replicas', key: 'replicas', width: 100 },
    { title: '🧠 CPU', dataIndex: 'cpu_limit', key: 'cpu_limit', width: 90 },
    { title: '💾 Memory', dataIndex: 'memory_limit', key: 'memory_limit', width: 100 },
    {
      title: '📡 Pod Status', key: 'status',
      render: (_, record) => {
        const status = record.status;
        if (!status) {
          return <Tag style={{ background: 'rgba(148,163,184,0.12)', borderColor: 'transparent', color: PALETTE.textDim }}>💤 No report yet</Tag>;
        }
        if (status.error) {
          return <Tag color="error" style={{ borderRadius: 6 }}>💥 {status.error}</Tag>;
        }
        return (
          <Space direction="vertical" size={6}>
            <Tag
              color={status.ready ? 'success' : 'processing'}
              style={{ borderRadius: 6, marginInlineEnd: 0 }}
            >
              {status.ready ? '✅ Ready' : '🚀 Launching'}
            </Tag>
            {status.pods?.map((pod) => (
              <Tooltip key={pod.pod_name} title={`Phase: ${pod.phase}`}>
                <Tag
                  icon={pod.ready ? <CheckCircleOutlined /> : <SyncOutlined spin />}
                  style={{
                    borderRadius: 6, marginInlineEnd: 0,
                    background: 'rgba(59, 130, 246, 0.10)',
                    borderColor: 'rgba(59, 130, 246, 0.25)',
                    color: '#bfdbfe',
                  }}
                >
                  {phaseEmoji(pod.phase)} {pod.pod_name.slice(-10)}
                </Tag>
              </Tooltip>
            ))}
          </Space>
        );
      },
    },
    {
      title: '⚙️ Actions', key: 'actions', width: 100, align: 'center',
      render: (_, record) => (
        <Space size={4}>
          <Tooltip title="Edit app ✏️">
            <Button type="text" style={{ color: PALETTE.accent }} icon={<EditOutlined />} onClick={() => openEditAppModal(record)} />
          </Tooltip>
          <Popconfirm
            title="Delete this app?"
            description="Its pods will be destroyed ☄️"
            okText="Delete"
            okButtonProps={{ danger: true }}
            onConfirm={() => handleDeleteApp(record.id)}
          >
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  /* ─────────── 🖥️ Render ─────────── */

  return (
    <ConfigProvider theme={spaceTheme}>
      <style>{GLOBAL_CSS}</style>

      <Layout className="k8s-shell">
        <div className="starfield" />

        {/* 🌠 Top bar */}
        <Header
          style={{
            position: 'sticky', top: 0, zIndex: 20,
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            paddingInline: 28,
            background: 'rgba(7, 10, 22, 0.75)',
            backdropFilter: 'blur(14px)',
            borderBottom: '1px solid rgba(99, 130, 246, 0.18)',
          }}
        >
          <Space size={14}>
            <span style={{ fontSize: 30, filter: 'drop-shadow(0 0 10px rgba(59, 130, 246, 0.8))' }}>🪐</span>
            <div style={{ lineHeight: 1.25 }}>
              <div className="gradient-text" style={{ fontSize: 19, fontWeight: 800, letterSpacing: 0.5 }}>
                K8s Mission Control
              </div>
              <Text style={{ fontSize: 12, color: PALETTE.textDim }}>Kubernetes Management Dashboard</Text>
            </div>
          </Space>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={openClusterModal}
            style={{ boxShadow: '0 0 18px rgba(59, 130, 246, 0.45)' }}
          >
            Connect Cluster 🌌
          </Button>
        </Header>

        <Layout>
          {/* 🛰️ Clusters sidebar */}
          <Sider width={280} className="cluster-sider">
            <div style={{
              padding: '18px 18px 10px',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            }}>
              <span style={{ fontWeight: 700, letterSpacing: 1.5, fontSize: 13, color: '#93c5fd' }}>
                🪐 CLUSTERS
              </span>
              <Tag style={{
                background: 'rgba(59, 130, 246, 0.15)', borderColor: 'transparent',
                color: '#93c5fd', borderRadius: 999, marginInlineEnd: 0,
              }}>
                {clusters.length}
              </Tag>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', padding: '0 4px 8px' }}>
              {clusters.length === 0 ? (
                <div style={{ padding: '32px 16px' }}>
                  <Empty
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    description={
                      <span style={{ color: PALETTE.textDim, fontSize: 13 }}>
                        🛰️ No clusters connected yet
                      </span>
                    }
                  />
                </div>
              ) : (
                <Menu
                  mode="inline"
                  selectedKeys={selectedCluster ? [String(selectedCluster.id)] : []}
                  items={clusterItems}
                />
              )}
            </div>

            <div style={{ padding: 12, borderTop: '1px solid rgba(99, 130, 246, 0.15)' }}>
              <Button type="primary" ghost block icon={<PlusOutlined />} onClick={openClusterModal}>
                🌌 Connect Cluster
              </Button>
            </div>
          </Sider>

          {/* Content Area */}
          <Content style={{ position: 'relative', zIndex: 1, padding: '24px 32px' }}>
            <div style={{ maxWidth: 1400, margin: '0 auto' }}>

              {/* 📊 Stats row */}
              <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
                {stats.map((s) => (
                  <Col xs={12} md={6} key={s.label}>
                    <Card className="glass-card stat-card" style={{ borderRadius: 14 }}>
                      <Statistic
                        title={<span style={{ fontSize: 13 }}>{s.emoji} {s.label}</span>}
                        value={s.value}
                        valueStyle={{ color: s.color, fontWeight: 700, fontSize: 30 }}
                      />
                    </Card>
                  </Col>
                ))}
              </Row>

              <Breadcrumb
                style={{ marginBottom: 16 }}
                items={[
                  { title: <span style={{ color: PALETTE.textDim }}>🪐 {selectedCluster?.name || 'No cluster selected'}</span> },
                  ...(selectedNamespace
                    ? [{ title: <span style={{ color: '#93c5fd' }}>📂 {selectedNamespace.name}</span> }]
                    : []),
                ]}
              />

              {selectedCluster ? (
                <Row gutter={[20, 20]}>
                  {/* 🗂️ Namespaces panel */}
                  <Col xs={24} lg={8}>
                    <Card
                      className="glass-card"
                      style={{ borderRadius: 14 }}
                      title={<Space size={8}><span style={{ fontSize: 17 }}>📂</span><span>Namespaces</span></Space>}
                      extra={
                        <Button type="primary" size="small" icon={<PlusOutlined />} onClick={openNsModal}>
                          ✨ New
                        </Button>
                      }
                    >
                      {namespaces.length === 0 ? (
                        <Empty
                          image={Empty.PRESENTED_IMAGE_SIMPLE}
                          description={<span style={{ color: PALETTE.textDim }}>🗂️ No namespaces yet — create one! ✨</span>}
                        />
                      ) : (
                        <Menu
                          mode="inline"
                          style={{ background: 'transparent', borderInlineEnd: 'none' }}
                          selectedKeys={selectedNamespace ? [String(selectedNamespace.id)] : []}
                          items={namespaces.map((ns) => ({
                            key: String(ns.id),
                            icon: <span style={{ fontSize: 14 }}>📁</span>,
                            label: (
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <span>{ns.name}</span>
                                <Popconfirm
                                  title="Delete this namespace?"
                                  description="This cannot be undone ⚠️"
                                  okText="Delete"
                                  okButtonProps={{ danger: true }}
                                  onConfirm={() => handleDeleteNamespace(ns.id)}
                                >
                                  <DeleteOutlined style={{ color: PALETTE.red }} onClick={(e) => e.stopPropagation()} />
                                </Popconfirm>
                              </div>
                            ),
                            onClick: () => {
                              setSelectedNamespace(ns);
                              fetchApps(ns.id);
                            },
                          }))}
                        />
                      )}
                    </Card>
                  </Col>

                  {/* 🚀 Apps panel */}
                  <Col xs={24} lg={16}>
                    {selectedNamespace ? (
                      <Card
                        className="glass-card"
                        style={{ borderRadius: 14 }}
                        title={
                          <Space size={8}>
                            <span style={{ fontSize: 17 }}>🚀</span>
                            <span>Apps in <Text code style={{ color: '#93c5fd' }}>{selectedNamespace.name}</Text></span>
                          </Space>
                        }
                        extra={
                          <Space>
                            <Tooltip title="Refresh status 🔄">
                              <Button icon={<ReloadOutlined />} onClick={() => fetchApps(selectedNamespace.id)} />
                            </Tooltip>
                            <Button type="primary" icon={<PlusOutlined />} onClick={openCreateAppModal}>
                              Deploy New App
                            </Button>
                          </Space>
                        }
                      >
                        <Table
                          dataSource={apps}
                          columns={appColumns}
                          rowKey="id"
                          loading={loading}
                          pagination={false}
                          locale={{
                            emptyText: (
                              <Empty
                                image={Empty.PRESENTED_IMAGE_SIMPLE}
                                description={<span style={{ color: PALETTE.textDim }}>🛰️ No apps deployed here yet — launch your first one!</span>}
                              />
                            ),
                          }}
                        />
                      </Card>
                    ) : (
                      <Card className="glass-card" style={{ borderRadius: 14, textAlign: 'center', padding: '40px 16px' }}>
                        <Empty
                          image={Empty.PRESENTED_IMAGE_SIMPLE}
                          description={<span style={{ color: PALETTE.textDim }}>🧭 Select a namespace to explore its apps</span>}
                        />
                      </Card>
                    )}
                  </Col>
                </Row>
              ) : (
                /* 🌌 Welcome screen */
                <Card className="glass-card" style={{ borderRadius: 16, textAlign: 'center', padding: '48px 24px' }}>
                  <div style={{ fontSize: 72, filter: 'drop-shadow(0 0 24px rgba(59, 130, 246, 0.6))' }}>🌌</div>
                  <Title level={3} className="gradient-text" style={{ marginTop: 16 }}>
                    Welcome to Mission Control
                  </Title>
                  <Text type="secondary" style={{ fontSize: 15 }}>
                    No cluster connected yet. Connect your first cluster and start exploring. 🚀
                  </Text>
                  <div style={{ marginTop: 28 }}>
                    <Button
                      type="primary"
                      size="large"
                      icon={<PlusOutlined />}
                      onClick={openClusterModal}
                      style={{ boxShadow: '0 0 20px rgba(59, 130, 246, 0.5)' }}
                    >
                      Connect Your First Cluster
                    </Button>
                  </div>
                </Card>
              )}
            </div>
          </Content>
        </Layout>

        <Footer style={{ position: 'relative', zIndex: 1, textAlign: 'center', background: 'transparent', color: PALETTE.textDim, fontSize: 13 }}>
          ⚡ K8s Mission Control · Exploring your cluster galaxy, one pod at a time 🌠
        </Footer>

        {/* 🌌 Modal: Connect Cluster */}
        <Modal
          title={<span>🌌 Connect New Cluster</span>}
          open={isClusterModalOpen}
          onCancel={() => setIsClusterModalOpen(false)}
          onOk={() => clusterForm.submit()}
          okText="🛰️ Connect"
        >
          <Form form={clusterForm} layout="vertical" onFinish={handleCreateCluster}>
            <Form.Item name="name" label="🏷️ Cluster Name" rules={[{ required: true, message: 'Please enter a cluster name' }]}>
              <Input prefix={<ClusterOutlined style={{ color: PALETTE.textDim }} />} placeholder="production-cluster-01" />
            </Form.Item>
            <Form.Item name="address" label="🌐 API Server Address" rules={[{ required: true, message: 'Please enter the API address' }]}>
              <Input prefix={<GlobalOutlined style={{ color: PALETTE.textDim }} />} placeholder="https://172.20.222.101:6443" />
            </Form.Item>
            <Form.Item name="token" label="🔑 Bearer Token" rules={[{ required: true, message: 'Please enter the token' }]}>
              <Input.Password prefix={<LockOutlined style={{ color: PALETTE.textDim }} />} placeholder="eyJhbGciOi..." />
            </Form.Item>
          </Form>
        </Modal>

        {/* 📦 Modal: Create Namespace */}
        <Modal
          title={<span>📦 Create Namespace</span>}
          open={isNsModalOpen}
          onCancel={() => setIsNsModalOpen(false)}
          onOk={() => namespaceForm.submit()}
          okText="✨ Create"
        >
          <Form form={namespaceForm} layout="vertical" onFinish={handleCreateNamespace}>
            <Form.Item name="name" label="🗂️ Namespace Name" rules={[{ required: true, message: 'Please enter a namespace name' }]}>
              <Input prefix={<span style={{ color: PALETTE.textDim }}>📁</span>} placeholder="my-team-dev" />
            </Form.Item>
          </Form>
        </Modal>

        {/* 🚀 Modal: Deploy / Edit App */}
        <Modal
          title={editingApp ? <span>✏️ Edit App — {editingApp.name}</span> : <span>🚀 Deploy a New App</span>}
          open={isAppModalOpen}
          onCancel={() => setIsAppModalOpen(false)}
          onOk={() => appForm.submit()}
          okText={editingApp ? '💾 Save Changes' : '🚀 Deploy'}
        >
          <Form form={appForm} layout="vertical" onFinish={handleCreateOrUpdateApp}>
            {!editingApp && (
              <Form.Item name="name" label="🏷️ App Name" rules={[{ required: true, message: 'Please enter an app name' }]}>
                <Input prefix={<AppstoreOutlined style={{ color: PALETTE.textDim }} />} placeholder="my-awesome-api" />
              </Form.Item>
            )}
            <Form.Item name="image" label="🖼️ Docker Image" rules={[{ required: true, message: 'Please enter a docker image' }]}>
              <Input placeholder="nginx:latest" />
            </Form.Item>
            <Form.Item name="replicas" label="🔢 Replica Count" initialValue={1}>
              <InputNumber min={1} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="cpu_limit" label="🧠 CPU Limit" initialValue="500m">
              <Input placeholder="500m" />
            </Form.Item>
            <Form.Item name="memory_limit" label="💾 Memory Limit" initialValue="512Mi">
              <Input placeholder="512Mi" />
            </Form.Item>
          </Form>
        </Modal>
      </Layout>
    </ConfigProvider>
  );
}
