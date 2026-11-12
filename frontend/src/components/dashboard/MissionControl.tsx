import { useEffect, useState, useMemo } from 'react';
import {
  Activity,
  Play,
  BarChart3,
  History,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Sliders,
  Cpu,
  Layers,
  Clock,
  Eye,
  EyeOff,
  Radio,
  ChevronDown,
  ChevronUp,
  Info,
} from 'lucide-react';
import { apiService } from '../../services/api';
import {
  CompareResponseDTO,
  HistoryItemDTO,
  OptimizationResponseDTO,
  OptimizeRequestDTO,
  RFConfigDTO,
  RFLinkResultDTO,
  ScenarioDetailDTO,
  ScenarioSummaryDTO,
  SolverName,
} from '../../types';

export const MissionControl: React.FC = () => {
  // Backend & Scenario State
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [scenarios, setScenarios] = useState<ScenarioSummaryDTO[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('rf-demonstration');
  const [scenarioDetail, setScenarioDetail] = useState<ScenarioDetailDTO | null>(null);
  const [loadingScenario, setLoadingScenario] = useState<boolean>(false);

  // RF Configuration State (Initialized with Section 3 illustrative inputs)
  const [rfConfig, setRfConfig] = useState<RFConfigDTO>({
    frequency_mhz: 2400.0,
    tx_power_dbm: 20.0,
    tx_antenna_gain_dbi: 2.0,
    rx_antenna_gain_dbi: 2.0,
    rx_sensitivity_dbm: -100.0,
    system_loss_db: 3.0,
    fade_margin_db: 10.0,
    environment: 'open',
    excess_loss_db: 0.0,
    uav_altitude_m: 60.0,
    target_height_m: 1.5,
  });
  const [rfLinks, setRfLinks] = useState<RFLinkResultDTO[]>([]);
  const [simulatingRF, setSimulatingRF] = useState<boolean>(false);

  // Solver Configuration State
  const [solverName, setSolverName] = useState<SolverName>('qaoa');
  const [qaoaDepth, setQaoaDepth] = useState<number>(1);
  const [shots, setShots] = useState<number>(500);
  const [penalty, setPenalty] = useState<number>(7.0); // Tested canonical default
  const [maxIterations, setMaxIterations] = useState<number>(25);
  const [randomSeed, setRandomSeed] = useState<number>(42);

  // Execution & Results State
  const [optimizing, setOptimizing] = useState<boolean>(false);
  const [currentResult, setCurrentResult] = useState<OptimizationResponseDTO | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Benchmark Comparison State
  const [comparing, setComparing] = useState<boolean>(false);
  const [compareResults, setCompareResults] = useState<CompareResponseDTO | null>(null);
  const [activeTab, setActiveTab] = useState<'single' | 'benchmark' | 'history'>('single');

  // History State
  const [historyItems, setHistoryItems] = useState<HistoryItemDTO[]>([]);
  const [loadingHistory, setLoadingHistory] = useState<boolean>(false);

  // Map Visualization Controls
  const [showBeams, setShowBeams] = useState<boolean>(true);
  const [hoveredNode, setHoveredNode] = useState<{
    type: 'target' | 'waypoint';
    id: string;
    x: number;
    y: number;
    extra?: string;
  } | null>(null);

  // Collapsible Methodology
  const [showMethodology, setShowMethodology] = useState<boolean>(false);

  // Check health on mount
  useEffect(() => {
    const checkHealth = async () => {
      try {
        await apiService.getHealth();
        setBackendOnline(true);
      } catch {
        setBackendOnline(false);
      }
    };
    checkHealth();
  }, []);

  // Fetch scenarios list and default RF scenario on mount
  useEffect(() => {
    const loadInitialData = async () => {
      setLoadingScenario(true);
      try {
        const list = await apiService.listScenarios();
        setScenarios(list);
      } catch (err) {
        console.warn('Could not load scenario list:', err);
      }

      try {
        const rfDemo = await apiService.getRFDemonstrationScenario();
        setScenarioDetail(rfDemo);
        if (rfDemo.rf_config) setRfConfig(rfDemo.rf_config);
        if (rfDemo.rf_links) setRfLinks(rfDemo.rf_links);
      } catch (err) {
        console.warn('Falling back to canonical scenario:', err);
        try {
          const canonical = await apiService.getCanonicalScenario();
          setScenarioDetail(canonical);
          setSelectedScenarioId('canonical');
        } catch {
          // ignore
        }
      } finally {
        setLoadingScenario(false);
      }
    };
    loadInitialData();
  }, []);

  // Fetch history when history tab is opened
  useEffect(() => {
    if (activeTab === 'history') {
      loadHistory();
    }
  }, [activeTab]);

  const loadHistory = async () => {
    setLoadingHistory(true);
    try {
      const res = await apiService.getHistory(20, 0);
      setHistoryItems(res.items);
    } catch (err) {
      console.warn('Failed to load history:', err);
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleScenarioChange = async (id: string) => {
    setSelectedScenarioId(id);
    setLoadingScenario(true);
    setErrorMsg(null);
    try {
      let detail: ScenarioDetailDTO;
      if (id === 'canonical') {
        detail = await apiService.getCanonicalScenario();
        setRfLinks([]);
      } else if (id === 'rf-demonstration') {
        detail = await apiService.getRFDemonstrationScenario();
        if (detail.rf_config) setRfConfig(detail.rf_config);
        if (detail.rf_links) setRfLinks(detail.rf_links);
      } else {
        detail = await apiService.getScenario(id);
      }
      setScenarioDetail(detail);
      setCurrentResult(null);
      setCompareResults(null);
    } catch (err: unknown) {
      setErrorMsg((err as Error).message || 'Failed to load scenario');
    } finally {
      setLoadingScenario(false);
    }
  };

  // Recalculate RF Coverage
  const handleRecalculateRF = async () => {
    setSimulatingRF(true);
    setErrorMsg(null);
    try {
      const res = await apiService.simulateRF({
        scenario_name: 'RF Simulation — Custom Inputs',
        rf_config: rfConfig,
        k_coverage: scenarioDetail?.k_coverage || 3,
        targets: scenarioDetail?.targets,
        waypoints: scenarioDetail?.waypoints,
      });

      // Update scenario with new simulated coverage matrix
      if (scenarioDetail) {
        setScenarioDetail({
          ...scenarioDetail,
          coverage_matrix: res.coverage_matrix,
          rf_config: res.rf_config,
          rf_links: res.links,
        });
      }
      setRfLinks(res.links);
      setCurrentResult(null);
    } catch (err: unknown) {
      setErrorMsg((err as Error).message || 'RF simulation recalculation failed');
    } finally {
      setSimulatingRF(false);
    }
  };

  // Run single optimization
  const handleRunOptimization = async () => {
    if (!scenarioDetail) return;
    setOptimizing(true);
    setErrorMsg(null);
    try {
      const req: OptimizeRequestDTO = {
        scenario_id: selectedScenarioId,
        target_ids: scenarioDetail.target_ids,
        waypoint_ids: scenarioDetail.waypoint_ids,
        coverage_matrix: scenarioDetail.coverage_matrix,
        k_coverage: scenarioDetail.k_coverage,
        solver_name: solverName,
        qaoa_depth: qaoaDepth,
        shots: shots,
        penalty: penalty,
        max_iterations: maxIterations,
        random_seed: randomSeed,
        rf_config: selectedScenarioId === 'rf-demonstration' ? rfConfig : null,
      };
      const res = await apiService.runOptimization(req);
      setCurrentResult(res);
      setActiveTab('single');
    } catch (err: unknown) {
      setErrorMsg((err as Error).message || 'Optimization run failed');
    } finally {
      setOptimizing(false);
    }
  };

  // Run multi-solver benchmark comparison
  const handleRunComparison = async () => {
    if (!scenarioDetail) return;
    setComparing(true);
    setErrorMsg(null);
    try {
      const res = await apiService.compareSolvers({
        scenario_id: selectedScenarioId,
        target_ids: scenarioDetail.target_ids,
        waypoint_ids: scenarioDetail.waypoint_ids,
        coverage_matrix: scenarioDetail.coverage_matrix,
        k_coverage: scenarioDetail.k_coverage,
        solvers: ['milp', 'brute_force', 'greedy', 'qaoa'],
        qaoa_options: {
          qaoa_depth: qaoaDepth,
          shots: shots,
          penalty: penalty,
          max_iterations: maxIterations,
          random_seed: randomSeed,
        },
        rf_config: selectedScenarioId === 'rf-demonstration' ? rfConfig : null,
      });
      setCompareResults(res);
      setActiveTab('benchmark');
      const qaoaRes = res.results.find((r) => r.solver.name.toLowerCase() === 'qaoa');
      if (qaoaRes) {
        setCurrentResult(qaoaRes);
      } else if (res.results.length > 0) {
        setCurrentResult(res.results[0]);
      }
    } catch (err: unknown) {
      setErrorMsg((err as Error).message || 'Benchmark comparison failed');
    } finally {
      setComparing(false);
    }
  };

  // Load a past run from history
  const handleSelectHistoryRun = async (runId: string) => {
    try {
      const detail = await apiService.getHistoryDetail(runId);
      if (detail && detail.result_data) {
        const reconstructed: OptimizationResponseDTO = {
          run_id: detail.run_id,
          status: detail.status,
          scenario: {
            id: (detail.request_data?.scenario_id as string) || 'canonical',
            name: detail.scenario_name,
            k_coverage: (detail.request_data?.k_coverage as number) || 3,
          },
          solver: {
            name: detail.solver_name,
            parameters: (detail.request_data as Record<string, unknown>) || {},
          },
          result: {
            selected_waypoint_ids: (detail.result_data.selected_waypoint_ids as string[]) || [],
            selected_waypoint_count: detail.selected_waypoint_count || 0,
            coverage_counts: (detail.result_data.coverage_counts as Record<string, number>) || {},
            feasible: detail.feasible || false,
            objective_value: detail.objective_value || 0,
            runtime_seconds: detail.runtime_seconds || 0,
          },
          metadata: (detail.result_data.metadata as Record<string, unknown>) || {},
        };
        setCurrentResult(reconstructed);
        setActiveTab('single');
      }
    } catch (err: unknown) {
      setErrorMsg((err as Error).message || 'Could not load historical run');
    }
  };

  // Selected waypoint set from current solution
  const selectedWaypointIds = useMemo(() => {
    return new Set(currentResult?.result?.selected_waypoint_ids || []);
  }, [currentResult]);

  // Scaled coordinates for SVG canvas
  const mapWidth = 540;
  const mapHeight = 420;
  const padding = 55;

  const { targetNodes, waypointNodes } = useMemo(() => {
    if (!scenarioDetail) return { targetNodes: [], waypointNodes: [] };

    const rawTargets = scenarioDetail.targets || scenarioDetail.target_ids.map((id, i) => ({
      id,
      x: [300, 900, 1500, 600, 1300][i % 5],
      y: [300, 350, 400, 1200, 1250][i % 5],
      height_m: 1.5,
    }));

    const rawWaypoints = scenarioDetail.waypoints || scenarioDetail.waypoint_ids.map((id, i) => ({
      id,
      x: [200, 800, 1400, 400, 1100, 1550][i % 6],
      y: [200, 250, 300, 1100, 1100, 1350][i % 6],
      altitude_m: 60.0,
      cost: 1.0,
    }));

    const allX = [...rawTargets.map((t) => t.x), ...rawWaypoints.map((w) => w.x)];
    const allY = [...rawTargets.map((t) => t.y), ...rawWaypoints.map((w) => w.y)];
    const minX = Math.min(...allX);
    const maxX = Math.max(...allX);
    const minY = Math.min(...allY);
    const maxY = Math.max(...allY);

    const spanX = Math.max(1, maxX - minX);
    const spanY = Math.max(1, maxY - minY);

    const scaleX = (x: number) => padding + ((x - minX) / spanX) * (mapWidth - 2 * padding);
    const scaleY = (y: number) => mapHeight - (padding + ((y - minY) / spanY) * (mapHeight - 2 * padding));

    const tNodes = rawTargets.map((t) => ({
      ...t,
      svgX: scaleX(t.x),
      svgY: scaleY(t.y),
    }));

    const wNodes = rawWaypoints.map((w) => ({
      ...w,
      svgX: scaleX(w.x),
      svgY: scaleY(w.y),
    }));

    return { targetNodes: tNodes, waypointNodes: wNodes };
  }, [scenarioDetail]);

  // Sensing lines connecting selected waypoints to covered targets
  const sensingLines = useMemo(() => {
    if (!scenarioDetail || !scenarioDetail.coverage_matrix) return [];
    const lines: Array<{
      targetId: string;
      waypointId: string;
      x1: number;
      y1: number;
      x2: number;
      y2: number;
      selected: boolean;
      linkMargin?: number;
    }> = [];

    const tMap = new Map(targetNodes.map((t) => [t.id, t]));
    const wMap = new Map(waypointNodes.map((w) => [w.id, w]));
    const linkMap = new Map(rfLinks.map((l) => [`${l.target_id}_${l.waypoint_id}`, l]));

    scenarioDetail.target_ids.forEach((tId, tIdx) => {
      scenarioDetail.waypoint_ids.forEach((wId, wIdx) => {
        if (scenarioDetail.coverage_matrix[tIdx][wIdx] === 1) {
          const tNode = tMap.get(tId);
          const wNode = wMap.get(wId);
          const lData = linkMap.get(`${tId}_${wId}`);
          if (tNode && wNode) {
            lines.push({
              targetId: tId,
              waypointId: wId,
              x1: wNode.svgX,
              y1: wNode.svgY,
              x2: tNode.svgX,
              y2: tNode.svgY,
              selected: selectedWaypointIds.has(wId),
              linkMargin: lData?.link_margin_db,
            });
          }
        }
      });
    });

    return lines;
  }, [scenarioDetail, targetNodes, waypointNodes, selectedWaypointIds, rfLinks]);

  // Lookup for RF link details
  const rfLinkLookup = useMemo(() => {
    const map = new Map<string, RFLinkResultDTO>();
    for (const l of rfLinks) {
      map.set(`${l.target_id}_${l.waypoint_id}`, l);
    }
    return map;
  }, [rfLinks]);

  return (
    <section id="mission-control" className="w-full bg-[#F7F5EF] text-[#141516] py-16 px-4 sm:px-8 border-t border-[#e2dedd]">
      <div className="max-w-7xl mx-auto space-y-8 font-sans">
        
        {/* 1. Compact Mission Header */}
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-6 border-b border-[#e2dedd]">
          <div>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-white border border-[#e2dedd] shadow-sm text-[#141516]">
                <Radio className="w-5 h-5 text-emerald-600" />
              </div>
              <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#141516]">
                UAV Mission Control &amp; RF Multi-Coverage Telemetry
              </h2>
            </div>
            <p className="text-[#8f8b8a] text-sm mt-1">
              Deterministic Cartesian simulation of UAV sensing waypoints and ground beacon links for $k$-coverage optimization.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div
              className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-mono font-medium border ${
                backendOnline === true
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                  : backendOnline === false
                  ? 'bg-rose-50 border-rose-200 text-rose-800'
                  : 'bg-slate-100 border-slate-200 text-slate-600'
              }`}
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  backendOnline === true
                    ? 'bg-emerald-600 animate-pulse'
                    : backendOnline === false
                    ? 'bg-rose-600'
                    : 'bg-slate-400'
                }`}
              />
              <span>
                {backendOnline === true
                  ? 'FASTAPI BACKEND: ONLINE'
                  : backendOnline === false
                  ? 'BACKEND: OFFLINE (PORT 8000)'
                  : 'CONNECTING...'}
              </span>
            </div>

            <button
              onClick={() => handleScenarioChange(selectedScenarioId)}
              className="p-2 rounded-lg bg-white hover:bg-slate-50 text-[#141516] border border-[#e2dedd] shadow-sm transition-colors"
              title="Reload scenario"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Global Error Banner */}
        {errorMsg && (
          <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-center justify-between shadow-sm">
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0" />
              <span>{errorMsg}</span>
            </div>
            <button
              onClick={() => setErrorMsg(null)}
              className="text-xs font-mono text-rose-700 hover:underline ml-4"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Navigation Tabs (Single Run, Multi-Solver Benchmark, Run History) */}
        <div className="flex items-center gap-3 border-b border-[#e2dedd] pb-2">
          <button
            onClick={() => setActiveTab('single')}
            className={`px-4 py-2 rounded-lg text-xs font-bold tracking-wider transition-all flex items-center gap-2 ${
              activeTab === 'single'
                ? 'bg-white text-[#141516] shadow-sm border border-[#e2dedd]'
                : 'text-[#8f8b8a] hover:text-[#141516]'
            }`}
          >
            <Activity className="w-4 h-4" />
            <span>MISSION RADAR &amp; SOLVER</span>
          </button>
          <button
            onClick={() => {
              setActiveTab('benchmark');
              if (!compareResults) handleRunComparison();
            }}
            className={`px-4 py-2 rounded-lg text-xs font-bold tracking-wider transition-all flex items-center gap-2 ${
              activeTab === 'benchmark'
                ? 'bg-white text-[#141516] shadow-sm border border-[#e2dedd]'
                : 'text-[#8f8b8a] hover:text-[#141516]'
            }`}
          >
            <BarChart3 className="w-4 h-4" />
            <span>4-SOLVER BENCHMARK</span>
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`px-4 py-2 rounded-lg text-xs font-bold tracking-wider transition-all flex items-center gap-2 ${
              activeTab === 'history'
                ? 'bg-white text-[#141516] shadow-sm border border-[#e2dedd]'
                : 'text-[#8f8b8a] hover:text-[#141516]'
            }`}
          >
            <History className="w-4 h-4" />
            <span>RUN HISTORY</span>
          </button>
        </div>

        {/* Tab 1: Single Solver Execution, RF Config & Radar Map */}
        {activeTab === 'single' && (
          <div className="space-y-8">
            
            {/* Top Grid: Scenario Selector & RF Link-Budget Controls */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              
              {/* Scenario Selection Card (4 cols) */}
              <div className="lg:col-span-4 p-6 rounded-2xl bg-white/90 backdrop-blur-md border border-[#e2dedd] shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-[#e2dedd] pb-3">
                  <h3 className="font-bold text-base text-[#141516] flex items-center gap-2">
                    <Layers className="w-4 h-4 text-emerald-600" />
                    SAR Scenario Selection
                  </h3>
                  <span className="text-[11px] font-mono text-[#8f8b8a] bg-slate-100 px-2 py-0.5 rounded">
                    k = {scenarioDetail?.k_coverage || 3}-fold
                  </span>
                </div>

                <div>
                  <label className="block text-xs font-mono text-[#8f8b8a] mb-1.5 uppercase">
                    Active Mission Dataset
                  </label>
                  <select
                    value={selectedScenarioId}
                    onChange={(e) => handleScenarioChange(e.target.value)}
                    disabled={loadingScenario}
                    className="w-full bg-[#F7F5EF] border border-[#e2dedd] rounded-lg px-3.5 py-2.5 text-xs font-medium text-[#141516] focus:outline-none focus:border-emerald-600"
                  >
                    {scenarios.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name} ({s.target_count}T, {s.waypoint_count}W)
                      </option>
                    ))}
                  </select>
                </div>

                {scenarioDetail && (
                  <div className="space-y-2 text-xs">
                    <div className="p-3 rounded-lg bg-[#F7F5EF] border border-[#e2dedd] space-y-1">
                      <div className="font-semibold text-[#141516]">{scenarioDetail.name}</div>
                      <div className="text-[#8f8b8a] text-[11px] leading-relaxed">
                        {scenarioDetail.scenario_type === 'rf_simulation'
                          ? 'Derived via 3D Free-Space Path Loss (FSPL) and illustrative link budget in local Cartesian coordinates (m).'
                          : 'Deterministic synthetic binary coverage matrix benchmark for mathematical solver validation.'}
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-2 text-center font-mono text-xs pt-1">
                      <div className="p-2 rounded bg-[#F7F5EF] border border-[#e2dedd]">
                        <div className="text-[10px] text-[#8f8b8a]">TARGETS</div>
                        <div className="font-bold text-rose-600 mt-0.5">{scenarioDetail.target_ids.length}</div>
                      </div>
                      <div className="p-2 rounded bg-[#F7F5EF] border border-[#e2dedd]">
                        <div className="text-[10px] text-[#8f8b8a]">WAYPOINTS</div>
                        <div className="font-bold text-emerald-600 mt-0.5">{scenarioDetail.waypoint_ids.length}</div>
                      </div>
                      <div className="p-2 rounded bg-[#F7F5EF] border border-[#e2dedd]">
                        <div className="text-[10px] text-[#8f8b8a]">REQUIRED k</div>
                        <div className="font-bold text-amber-600 mt-0.5">k={scenarioDetail.k_coverage}</div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* 3. RF Configuration Section (8 cols) */}
              <div className="lg:col-span-8 p-6 rounded-2xl bg-white/90 backdrop-blur-md border border-[#e2dedd] shadow-sm space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#e2dedd] pb-3">
                  <div>
                    <h3 className="font-bold text-base text-[#141516] flex items-center gap-2">
                      <Radio className="w-4 h-4 text-emerald-600" />
                      RF Link-Budget Simulation Parameters
                    </h3>
                    <p className="text-[11px] text-[#8f8b8a]">
                      Simulation parameters — not real-world measurements or hardware control commands.
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={handleRecalculateRF}
                    disabled={simulatingRF}
                    className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-mono text-xs font-semibold tracking-wider transition-all flex items-center gap-2 shadow-sm self-start sm:self-auto disabled:opacity-50"
                  >
                    {simulatingRF ? (
                      <span className="flex items-center gap-1.5">
                        <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        RECALCULATING...
                      </span>
                    ) : (
                      <span>RECALCULATE RF COVERAGE</span>
                    )}
                  </button>
                </div>

                {/* RF Inputs Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
                  <div>
                    <label className="text-[#8f8b8a] block mb-1">Carrier Freq (MHz)</label>
                    <input
                      type="number"
                      step={10}
                      min={100}
                      value={rfConfig.frequency_mhz}
                      onChange={(e) => setRfConfig({ ...rfConfig, frequency_mhz: Math.max(1, Number(e.target.value)) })}
                      className="w-full bg-[#F7F5EF] border border-[#e2dedd] rounded px-2.5 py-1.5 text-[#141516]"
                    />
                  </div>

                  <div>
                    <label className="text-[#8f8b8a] block mb-1">Tx Power (dBm)</label>
                    <input
                      type="number"
                      step={1}
                      value={rfConfig.tx_power_dbm}
                      onChange={(e) => setRfConfig({ ...rfConfig, tx_power_dbm: Number(e.target.value) })}
                      className="w-full bg-[#F7F5EF] border border-[#e2dedd] rounded px-2.5 py-1.5 text-[#141516]"
                    />
                  </div>

                  <div>
                    <label className="text-[#8f8b8a] block mb-1">Tx Gain (dBi)</label>
                    <input
                      type="number"
                      step={0.5}
                      value={rfConfig.tx_antenna_gain_dbi}
                      onChange={(e) => setRfConfig({ ...rfConfig, tx_antenna_gain_dbi: Number(e.target.value) })}
                      className="w-full bg-[#F7F5EF] border border-[#e2dedd] rounded px-2.5 py-1.5 text-[#141516]"
                    />
                  </div>

                  <div>
                    <label className="text-[#8f8b8a] block mb-1">UAV Rx Gain (dBi)</label>
                    <input
                      type="number"
                      step={0.5}
                      value={rfConfig.rx_antenna_gain_dbi}
                      onChange={(e) => setRfConfig({ ...rfConfig, rx_antenna_gain_dbi: Number(e.target.value) })}
                      className="w-full bg-[#F7F5EF] border border-[#e2dedd] rounded px-2.5 py-1.5 text-[#141516]"
                    />
                  </div>

                  <div>
                    <label className="text-[#8f8b8a] block mb-1">Rx Sensitivity (dBm)</label>
                    <input
                      type="number"
                      step={1}
                      value={rfConfig.rx_sensitivity_dbm}
                      onChange={(e) => setRfConfig({ ...rfConfig, rx_sensitivity_dbm: Number(e.target.value) })}
                      className="w-full bg-[#F7F5EF] border border-[#e2dedd] rounded px-2.5 py-1.5 text-[#141516]"
                    />
                  </div>

                  <div>
                    <label className="text-[#8f8b8a] block mb-1">System Loss (dB)</label>
                    <input
                      type="number"
                      min={0}
                      step={0.5}
                      value={rfConfig.system_loss_db}
                      onChange={(e) => setRfConfig({ ...rfConfig, system_loss_db: Math.max(0, Number(e.target.value)) })}
                      className="w-full bg-[#F7F5EF] border border-[#e2dedd] rounded px-2.5 py-1.5 text-[#141516]"
                    />
                  </div>

                  <div>
                    <label className="text-[#8f8b8a] block mb-1">Fade Margin (dB)</label>
                    <input
                      type="number"
                      min={0}
                      step={1}
                      value={rfConfig.fade_margin_db}
                      onChange={(e) => setRfConfig({ ...rfConfig, fade_margin_db: Math.max(0, Number(e.target.value)) })}
                      className="w-full bg-[#F7F5EF] border border-[#e2dedd] rounded px-2.5 py-1.5 text-[#141516]"
                    />
                  </div>

                  <div>
                    <label className="text-[#8f8b8a] block mb-1">UAV Altitude (m)</label>
                    <input
                      type="number"
                      min={10}
                      step={5}
                      value={rfConfig.uav_altitude_m}
                      onChange={(e) => setRfConfig({ ...rfConfig, uav_altitude_m: Math.max(0, Number(e.target.value)) })}
                      className="w-full bg-[#F7F5EF] border border-[#e2dedd] rounded px-2.5 py-1.5 text-[#141516]"
                    />
                  </div>
                </div>

                {/* Environmental Selection & Explanatory Note */}
                <div className="pt-2 border-t border-[#e2dedd] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-xs font-mono">
                  <div className="flex items-center gap-3">
                    <span className="text-[#8f8b8a]">Environment:</span>
                    <select
                      value={rfConfig.environment}
                      onChange={(e) => {
                        const env = e.target.value;
                        const excess = env === 'urban' ? 12.0 : env === 'suburban' ? 5.0 : 0.0;
                        setRfConfig({ ...rfConfig, environment: env, excess_loss_db: excess });
                      }}
                      className="bg-[#F7F5EF] border border-[#e2dedd] rounded px-2.5 py-1 text-[#141516] font-medium"
                    >
                      <option value="open">1. Open / Line-of-Sight (0 dB excess loss)</option>
                      <option value="suburban">2. Suburban (5 dB assumed excess loss)</option>
                      <option value="urban">3. Urban / Obstructed (12 dB assumed excess loss)</option>
                    </select>
                  </div>

                  <div className="text-[11px] text-[#8f8b8a] flex items-center gap-1.5">
                    <Info className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" />
                    <span>Threshold: {rfConfig.rx_sensitivity_dbm + rfConfig.fade_margin_db} dBm | Excess losses are configurable assumptions.</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Middle Grid: 2D Radar Canvas & RF Link Analysis Tables */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              
              {/* 4. Target & Waypoint Visualization (Map - 6 cols) */}
              <div className="lg:col-span-6 p-6 rounded-2xl bg-white/90 backdrop-blur-md border border-[#e2dedd] shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-[#e2dedd] pb-3">
                  <div>
                    <h3 className="font-bold text-base text-[#141516] flex items-center gap-2">
                      <Radio className="w-4 h-4 text-emerald-600" />
                      2D Cartesian Mission Map (Metres)
                    </h3>
                    <p className="text-[11px] text-[#8f8b8a]">
                      Red: Ground Beacons (T1–T5) | Green: Active UAV Waypoints | Blue: Inactive
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={() => setShowBeams(!showBeams)}
                    className="px-2.5 py-1 rounded-lg bg-[#F7F5EF] hover:bg-slate-200 border border-[#e2dedd] text-xs font-mono text-[#141516] flex items-center gap-1.5 transition-colors"
                  >
                    {showBeams ? <Eye className="w-3.5 h-3.5 text-emerald-600" /> : <EyeOff className="w-3.5 h-3.5 text-[#8f8b8a]" />}
                    <span>{showBeams ? 'Links: ON' : 'Links: OFF'}</span>
                  </button>
                </div>

                {/* SVG Coordinate Map */}
                <div className="w-full aspect-[14/11] bg-[#F7F5EF] rounded-xl border border-[#e2dedd] overflow-hidden relative shadow-inner">
                  <svg viewBox={`0 0 ${mapWidth} ${mapHeight}`} className="w-full h-full select-none">
                    {/* Background Grid */}
                    <defs>
                      <pattern id="cartesianGrid" width="40" height="40" patternUnits="userSpaceOnUse">
                        <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#e2dedd" strokeWidth="1" />
                      </pattern>
                    </defs>
                    <rect width={mapWidth} height={mapHeight} fill="url(#cartesianGrid)" />

                    {/* Concentric Reference Circles */}
                    <circle cx={mapWidth / 2} cy={mapHeight / 2} r={mapHeight * 0.42} fill="none" stroke="#8f8b8a" strokeOpacity="0.15" strokeDasharray="3 3" />
                    <circle cx={mapWidth / 2} cy={mapHeight / 2} r={mapHeight * 0.25} fill="none" stroke="#8f8b8a" strokeOpacity="0.15" strokeDasharray="3 3" />

                    {/* Sensing Links */}
                    {showBeams &&
                      sensingLines.map((line, idx) => {
                        const margin = line.linkMargin ?? 0;
                        const linkColor = !line.selected
                          ? '#cbd5e1'
                          : margin >= 10
                          ? '#10b981'
                          : margin >= 0
                          ? '#f59e0b'
                          : '#ef4444';

                        return (
                          <line
                            key={idx}
                            x1={line.x1}
                            y1={line.y1}
                            x2={line.x2}
                            y2={line.y2}
                            stroke={linkColor}
                            strokeWidth={line.selected ? 2.0 : 0.8}
                            strokeDasharray={line.selected ? 'none' : '3 3'}
                            strokeOpacity={line.selected ? 0.85 : 0.4}
                          />
                        );
                      })}

                    {/* Waypoint Nodes */}
                    {waypointNodes.map((w) => {
                      const isSelected = selectedWaypointIds.has(w.id);
                      return (
                        <g
                          key={w.id}
                          className="cursor-pointer transition-transform hover:scale-125"
                          onMouseEnter={() =>
                            setHoveredNode({
                              type: 'waypoint',
                              id: w.id,
                              x: w.x,
                              y: w.y,
                              extra: isSelected ? 'SELECTED BY OPTIMIZER' : 'CANDIDATE SENSING WAYPOINT',
                            })
                          }
                          onMouseLeave={() => setHoveredNode(null)}
                        >
                          {isSelected && (
                            <circle cx={w.svgX} cy={w.svgY} r={16} fill="none" stroke="#10b981" strokeOpacity="0.3" className="animate-ping" />
                          )}
                          <circle
                            cx={w.svgX}
                            cy={w.svgY}
                            r={isSelected ? 9 : 6}
                            fill={isSelected ? '#10b981' : '#ffffff'}
                            stroke={isSelected ? '#059669' : '#64748b'}
                            strokeWidth={2}
                          />
                          <text
                            x={w.svgX}
                            y={w.svgY + (isSelected ? 20 : 16)}
                            fill={isSelected ? '#059669' : '#475569'}
                            fontSize={10}
                            fontFamily="JetBrains Mono, monospace"
                            textAnchor="middle"
                            fontWeight="bold"
                          >
                            {w.id}
                          </text>
                        </g>
                      );
                    })}

                    {/* Target Nodes */}
                    {targetNodes.map((t) => {
                      const covCount = currentResult?.result?.coverage_counts?.[t.id] ?? 0;
                      const reqK = scenarioDetail?.k_coverage || 3;
                      const isSatisfied = covCount >= reqK;

                      return (
                        <g
                          key={t.id}
                          className="cursor-pointer transition-transform hover:scale-125"
                          onMouseEnter={() =>
                            setHoveredNode({
                              type: 'target',
                              id: t.id,
                              x: t.x,
                              y: t.y,
                              extra: `Coverage: ${covCount}/${reqK}-fold requirement`,
                            })
                          }
                          onMouseLeave={() => setHoveredNode(null)}
                        >
                          <circle cx={t.svgX} cy={t.svgY} r={12} fill="none" stroke="#ef4444" strokeOpacity="0.25" />
                          <circle cx={t.svgX} cy={t.svgY} r={6} fill="#ef4444" stroke="#ffffff" strokeWidth={1.5} />
                          <text
                            x={t.svgX}
                            y={t.svgY - 10}
                            fill="#b91c1c"
                            fontSize={10}
                            fontFamily="JetBrains Mono, monospace"
                            textAnchor="middle"
                            fontWeight="bold"
                          >
                            {t.id}
                          </text>
                          {currentResult && (
                            <text
                              x={t.svgX}
                              y={t.svgY + 18}
                              fill={isSatisfied ? '#059669' : '#dc2626'}
                              fontSize={9}
                              fontFamily="JetBrains Mono, monospace"
                              textAnchor="middle"
                              fontWeight="bold"
                            >
                              {covCount}/{reqK}
                            </text>
                          )}
                        </g>
                      );
                    })}
                  </svg>

                  {/* Tooltip Overlay */}
                  {hoveredNode && (
                    <div className="absolute top-4 left-4 bg-white/95 border border-[#e2dedd] p-2.5 rounded-lg text-xs font-mono shadow-md pointer-events-none">
                      <div className="text-[#141516] font-bold">
                        {hoveredNode.type.toUpperCase()}: {hoveredNode.id}
                      </div>
                      <div className="text-[#8f8b8a]">
                        Coordinates: ({hoveredNode.x.toFixed(0)}m, {hoveredNode.y.toFixed(0)}m)
                      </div>
                      {hoveredNode.extra && <div className="text-emerald-700 font-medium mt-1">{hoveredNode.extra}</div>}
                    </div>
                  )}
                </div>

                {/* RF Legend */}
                <div className="flex flex-wrap items-center justify-between text-[11px] font-mono text-[#8f8b8a] pt-1 border-t border-[#e2dedd]">
                  <span>LINK STATUS:</span>
                  <div className="flex items-center gap-1.5 text-emerald-800">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                    <span>Strong (≥10 dB)</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-amber-800">
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                    <span>Marginal (0–10 dB)</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-rose-800">
                    <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
                    <span>Insufficient (&lt;0 dB)</span>
                  </div>
                </div>
              </div>

              {/* 5. RF Signal & Coverage Analysis (6 cols) */}
              <div className="lg:col-span-6 p-6 rounded-2xl bg-white/90 backdrop-blur-md border border-[#e2dedd] shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-[#e2dedd] pb-3">
                  <div>
                    <h3 className="font-bold text-base text-[#141516] flex items-center gap-2">
                      <BarChart3 className="w-4 h-4 text-emerald-600" />
                      RF Link Budget &amp; Coverage Matrix Audit
                    </h3>
                    <p className="text-[11px] text-[#8f8b8a]">
                      Pairwise 3D Distance, Received Power $P_r$ (dBm), and Link Margin (dB)
                    </p>
                  </div>
                </div>

                {/* Matrix Table */}
                {scenarioDetail && (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left font-mono text-[11px] border-collapse">
                      <thead>
                        <tr className="border-b border-[#e2dedd] text-[#8f8b8a] bg-[#F7F5EF]">
                          <th className="py-2 px-2.5">TARGET</th>
                          {scenarioDetail.waypoint_ids.map((wId) => (
                            <th key={wId} className="py-2 px-2 text-center">{wId}</th>
                          ))}
                          <th className="py-2 px-2.5 text-center">TOTAL COV</th>
                          <th className="py-2 px-2.5 text-center">STATUS</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#e2dedd]">
                        {scenarioDetail.target_ids.map((tId, tIdx) => {
                          const covCount = scenarioDetail.coverage_matrix[tIdx].reduce((a, b) => a + b, 0);
                          const satisfied = covCount >= scenarioDetail.k_coverage;

                          return (
                            <tr key={tId} className="hover:bg-slate-50 transition-colors">
                              <td className="py-2 px-2.5 font-bold text-[#141516]">{tId}</td>
                              {scenarioDetail.waypoint_ids.map((wId, wIdx) => {
                                const isCovered = scenarioDetail.coverage_matrix[tIdx][wIdx] === 1;
                                const link = rfLinkLookup.get(`${tId}_${wId}`);

                                return (
                                  <td key={wId} className="py-2 px-2 text-center">
                                    <div
                                      className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                        isCovered
                                          ? link && link.link_margin_db >= 10
                                            ? 'bg-emerald-100 text-emerald-800'
                                            : 'bg-amber-100 text-amber-800'
                                          : 'bg-rose-100 text-rose-800'
                                      }`}
                                      title={
                                        link
                                          ? `Dist: ${link.distance_3d_m}m | Pr: ${link.received_power_dbm} dBm | Margin: ${link.link_margin_db} dB`
                                          : 'Binary Coverage'
                                      }
                                    >
                                      {isCovered ? '1' : '0'}
                                    </div>
                                    {link && (
                                      <div className="text-[9px] text-[#8f8b8a] mt-0.5">
                                        {link.received_power_dbm.toFixed(0)}dBm
                                      </div>
                                    )}
                                  </td>
                                );
                              })}
                              <td className="py-2 px-2.5 text-center font-bold text-[#141516]">{covCount} / {scenarioDetail.waypoint_ids.length}</td>
                              <td className="py-2 px-2.5 text-center">
                                <span
                                  className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                    satisfied ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' : 'bg-rose-50 text-rose-800 border border-rose-200'
                                  }`}
                                >
                                  {satisfied ? 'PASS' : 'DEFICIENT'}
                                </span>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}

                <div className="text-[11px] text-[#8f8b8a] leading-relaxed bg-[#F7F5EF] p-3 rounded-lg border border-[#e2dedd]">
                  <strong>Mathematical Derivation:</strong> Binary coverage A_ji = 1 when predicted received power P_r &ge; P_threshold = P_rx_sens + M_fade = {rfConfig.rx_sensitivity_dbm + rfConfig.fade_margin_db} dBm. This binary matrix is passed directly to the classical and QAOA optimization solvers.
                </div>
              </div>
            </div>

            {/* Bottom Grid: Solver Selection & Execution Telemetry */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              
              {/* 6. Solver Selection & Controls (5 cols) */}
              <div className="lg:col-span-5 p-6 rounded-2xl bg-white/90 backdrop-blur-md border border-[#e2dedd] shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-[#e2dedd] pb-3">
                  <h3 className="font-bold text-base text-[#141516] flex items-center gap-2">
                    <Sliders className="w-4 h-4 text-emerald-600" />
                    Solver Selection &amp; Controls
                  </h3>
                </div>

                {/* 4 Solver Buttons */}
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setSolverName('qaoa')}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      solverName === 'qaoa'
                        ? 'bg-emerald-50 border-emerald-600 text-[#141516] shadow-sm'
                        : 'bg-[#F7F5EF] border-[#e2dedd] text-[#8f8b8a] hover:border-slate-400'
                    }`}
                  >
                    <div className="font-bold text-xs text-emerald-800">QAOA (Quantum)</div>
                    <div className="text-[10px] text-[#8f8b8a]">Qiskit Aer (16 Qubits)</div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setSolverName('milp')}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      solverName === 'milp'
                        ? 'bg-emerald-50 border-emerald-600 text-[#141516] shadow-sm'
                        : 'bg-[#F7F5EF] border-[#e2dedd] text-[#8f8b8a] hover:border-slate-400'
                    }`}
                  >
                    <div className="font-bold text-xs text-slate-900">SciPy MILP</div>
                    <div className="text-[10px] text-[#8f8b8a]">Branch-and-Cut (Exact)</div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setSolverName('brute_force')}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      solverName === 'brute_force'
                        ? 'bg-emerald-50 border-emerald-600 text-[#141516] shadow-sm'
                        : 'bg-[#F7F5EF] border-[#e2dedd] text-[#8f8b8a] hover:border-slate-400'
                    }`}
                  >
                    <div className="font-bold text-xs text-slate-900">Brute Force</div>
                    <div className="text-[10px] text-[#8f8b8a]">2^6 = 64 Subsets</div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setSolverName('greedy')}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      solverName === 'greedy'
                        ? 'bg-emerald-50 border-emerald-600 text-[#141516] shadow-sm'
                        : 'bg-[#F7F5EF] border-[#e2dedd] text-[#8f8b8a] hover:border-slate-400'
                    }`}
                  >
                    <div className="font-bold text-xs text-slate-900">Greedy</div>
                    <div className="text-[10px] text-[#8f8b8a]">Fast Polynomial Heuristic</div>
                  </button>
                </div>

                {/* QAOA Parameters */}
                {solverName === 'qaoa' && (
                  <div className="p-4 rounded-xl bg-[#F7F5EF] border border-[#e2dedd] space-y-3 font-mono text-xs">
                    <div className="text-[11px] font-bold text-emerald-800 flex items-center justify-between">
                      <span>QAOA HYPERPARAMETERS</span>
                      <Cpu className="w-3.5 h-3.5" />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-[#8f8b8a] block mb-1">Depth (p): {qaoaDepth}</label>
                        <input
                          type="range"
                          min={1}
                          max={3}
                          step={1}
                          value={qaoaDepth}
                          onChange={(e) => setQaoaDepth(Number(e.target.value))}
                          className="w-full accent-emerald-600 cursor-pointer"
                        />
                      </div>

                      <div>
                        <label className="text-[#8f8b8a] block mb-1">Shots: {shots}</label>
                        <input
                          type="range"
                          min={100}
                          max={1000}
                          step={100}
                          value={shots}
                          onChange={(e) => setShots(Number(e.target.value))}
                          className="w-full accent-emerald-600 cursor-pointer"
                        />
                      </div>

                      <div>
                        <label className="text-[#8f8b8a] block mb-1">Penalty λ: {penalty.toFixed(1)}</label>
                        <input
                          type="number"
                          step={0.5}
                          value={penalty}
                          onChange={(e) => setPenalty(Number(e.target.value))}
                          className="w-full bg-white border border-[#e2dedd] rounded px-2 py-1 text-xs text-[#141516]"
                        />
                        <div className="text-[10px] text-[#8f8b8a] mt-0.5">Tested default: λ = 7.0</div>
                      </div>

                      <div>
                        <label className="text-[#8f8b8a] block mb-1">Max Iterations: {maxIterations}</label>
                        <input
                          type="range"
                          min={10}
                          max={50}
                          step={5}
                          value={maxIterations}
                          onChange={(e) => setMaxIterations(Number(e.target.value))}
                          className="w-full accent-emerald-600 cursor-pointer"
                        />
                      </div>

                      <div className="col-span-2">
                        <label className="text-[#8f8b8a] block mb-1">Random Seed: {randomSeed}</label>
                        <input
                          type="number"
                          value={randomSeed}
                          onChange={(e) => setRandomSeed(Number(e.target.value) || 0)}
                          className="w-full bg-white border border-[#e2dedd] rounded px-2 py-1 text-xs text-[#141516]"
                        />
                      </div>
                    </div>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="space-y-2 pt-2">
                  <button
                    type="button"
                    onClick={handleRunOptimization}
                    disabled={optimizing || comparing}
                    className="w-full py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-sm tracking-wide transition-all shadow-sm flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    {optimizing ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        <span>OPTIMIZING IN PROGRESS...</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-4 h-4 fill-current" />
                        <span>RUN {solverName.toUpperCase()} OPTIMIZER</span>
                      </>
                    )}
                  </button>

                  <button
                    type="button"
                    onClick={handleRunComparison}
                    disabled={optimizing || comparing}
                    className="w-full py-2.5 px-4 rounded-xl bg-white hover:bg-slate-50 border border-[#e2dedd] text-[#141516] font-semibold text-xs tracking-wider transition-colors flex items-center justify-center gap-2 disabled:opacity-50 shadow-sm"
                  >
                    {comparing ? (
                      <>
                        <div className="w-3.5 h-3.5 border-2 border-[#141516] border-t-transparent rounded-full animate-spin" />
                        <span>BENCHMARKING ALL SOLVERS...</span>
                      </>
                    ) : (
                      <>
                        <BarChart3 className="w-4 h-4 text-emerald-600" />
                        <span>RUN MULTI-SOLVER BENCHMARK</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* 7. Optimization Results Telemetry (7 cols) */}
              <div className="lg:col-span-7 p-6 rounded-2xl bg-white/90 backdrop-blur-md border border-[#e2dedd] shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-[#e2dedd] pb-3">
                  <div className="flex items-center gap-2">
                    <h4 className="font-bold text-base text-[#141516]">
                      {currentResult ? `${currentResult.solver.name.toUpperCase()} Solver Telemetry` : 'Optimization Output'}
                    </h4>
                  </div>

                  {currentResult && (
                    <div
                      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold ${
                        currentResult.result.feasible
                          ? 'bg-emerald-50 text-emerald-800 border border-emerald-300'
                          : 'bg-rose-50 text-rose-800 border border-rose-300'
                      }`}
                    >
                      {currentResult.result.feasible ? (
                        <>
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                          <span>FEASIBLE (k={scenarioDetail?.k_coverage} MET)</span>
                        </>
                      ) : (
                        <>
                          <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
                          <span>INFEASIBLE</span>
                        </>
                      )}
                    </div>
                  )}
                </div>

                {currentResult ? (
                  <div className="space-y-4">
                    {/* Metric Cards */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center font-mono">
                      <div className="p-3 rounded-xl bg-[#F7F5EF] border border-[#e2dedd]">
                        <div className="text-[10px] text-[#8f8b8a]">SELECTED WAYPOINTS</div>
                        <div className="text-xl font-bold text-emerald-700 mt-1">
                          {currentResult.result.selected_waypoint_count} / {scenarioDetail?.waypoint_ids.length}
                        </div>
                        <div className="text-[10px] text-[#8f8b8a] truncate mt-0.5">
                          [{currentResult.result.selected_waypoint_ids.join(', ')}]
                        </div>
                      </div>

                      <div className="p-3 rounded-xl bg-[#F7F5EF] border border-[#e2dedd]">
                        <div className="text-[10px] text-[#8f8b8a]">OBJECTIVE VALUE</div>
                        <div className="text-xl font-bold text-[#141516] mt-1">
                          {currentResult.result.objective_value.toFixed(1)}
                        </div>
                        <div className="text-[10px] text-[#8f8b8a] mt-0.5">Waypoints Used</div>
                      </div>

                      <div className="p-3 rounded-xl bg-[#F7F5EF] border border-[#e2dedd]">
                        <div className="text-[10px] text-[#8f8b8a]">RUNTIME</div>
                        <div className="text-xl font-bold text-slate-800 mt-1 flex items-center justify-center gap-1">
                          <Clock className="w-3.5 h-3.5 text-[#8f8b8a]" />
                          <span>{(currentResult.result.runtime_seconds * 1000).toFixed(1)} ms</span>
                        </div>
                        <div className="text-[10px] text-[#8f8b8a] mt-0.5">
                          {currentResult.result.runtime_seconds.toFixed(4)} s
                        </div>
                      </div>

                      <div className="p-3 rounded-xl bg-[#F7F5EF] border border-[#e2dedd]">
                        <div className="text-[10px] text-[#8f8b8a]">SAMPLING YIELD</div>
                        <div className="text-xl font-bold text-indigo-700 mt-1">
                          {currentResult.metadata.feasible_rate !== undefined
                            ? `${(Number(currentResult.metadata.feasible_rate) * 100).toFixed(1)}%`
                            : '100%'}
                        </div>
                        <div className="text-[10px] text-[#8f8b8a] mt-0.5">
                          {currentResult.metadata.feasible_rate !== undefined ? 'QAOA Feasible Rate' : 'Deterministic'}
                        </div>
                      </div>
                    </div>

                    {/* Coverage Audit Box */}
                    <div className="p-3 rounded-xl bg-[#F7F5EF] border border-[#e2dedd]">
                      <div className="text-xs font-mono text-[#8f8b8a] mb-2">TARGET MULTI-COVERAGE AUDIT</div>
                      <div className="grid grid-cols-5 gap-2 font-mono text-xs">
                        {scenarioDetail?.target_ids.map((tId) => {
                          const count = currentResult.result.coverage_counts[tId] || 0;
                          const reqK = scenarioDetail?.k_coverage || 3;
                          const pass = count >= reqK;

                          return (
                            <div
                              key={tId}
                              className={`p-2 rounded text-center border ${
                                pass
                                  ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                                  : 'bg-rose-50 border-rose-200 text-rose-800'
                              }`}
                            >
                              <div className="font-bold">{tId}</div>
                              <div className="text-sm font-extrabold mt-0.5">{count} / {reqK}</div>
                              <div className="text-[10px]">{pass ? 'SATISFIED' : 'DEFICIT'}</div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="py-16 text-center text-[#8f8b8a] text-xs font-mono">
                    Select a solver on the left and click &quot;Run Optimizer&quot; to inspect real-time solution telemetry.
                  </div>
                )}
              </div>
            </div>

            {/* 9. Collapsible Optimization Methodology & Technical Details */}
            <div className="rounded-2xl bg-white/90 backdrop-blur-md border border-[#e2dedd] shadow-sm overflow-hidden">
              <button
                type="button"
                onClick={() => setShowMethodology(!showMethodology)}
                className="w-full p-4 flex items-center justify-between text-left hover:bg-slate-50 transition-colors"
              >
                <div className="flex items-center gap-2 font-bold text-sm text-[#141516]">
                  <Info className="w-4 h-4 text-emerald-600" />
                  <span>Optimization Methodology, Search Spaces &amp; Mathematical Rigor</span>
                </div>
                {showMethodology ? <ChevronUp className="w-4 h-4 text-[#8f8b8a]" /> : <ChevronDown className="w-4 h-4 text-[#8f8b8a]" />}
              </button>

              {showMethodology && (
                <div className="p-6 pt-2 border-t border-[#e2dedd] space-y-4 text-xs text-[#141516] font-sans leading-relaxed">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                      <div className="font-bold text-xs uppercase tracking-wider text-[#8f8b8a]">
                        Search Space Demarcation
                      </div>
                      <p>
                        It is critical to distinguish between the classical subset exploration and the quantum QUBO state space:
                      </p>
                      <ul className="list-disc list-inside space-y-1 font-mono text-[11px] text-[#141516] bg-[#F7F5EF] p-3 rounded-lg border border-[#e2dedd]">
                        <li>
                          <strong>Classical Waypoint Subsets:</strong> For N=6 waypoints, there are exactly 2^6 = 64 candidate subsets evaluated by exhaustive enumeration.
                        </li>
                        <li>
                          <strong>Full QUBO / QAOA State Space:</strong> 6 waypoint variables + 10 slack variables (2 per target) = 16 binary variables, spanning 2^16 = 65,536 bitstrings.
                        </li>
                      </ul>
                      <p className="text-[11px] text-[#8f8b8a]">
                        The QAOA quantum circuit operates directly on the 16-qubit Hilbert space without reducing the problem to classical subsets.
                      </p>
                    </div>

                    <div className="space-y-2">
                      <div className="font-bold text-xs uppercase tracking-wider text-[#8f8b8a]">
                        QUBO Formulation &amp; Penalty Guarantee
                      </div>
                      <p>
                        The constrained problem is mapped to an unconstrained objective $H_C$:
                      </p>
                      <div className="p-3 rounded-lg bg-[#F7F5EF] border border-[#e2dedd] font-mono text-[11px] text-[#141516] overflow-x-auto">
                        H_C(x, b) = sum_i x_i + lambda * sum_j ( sum_i A_ji x_i - k - b_j0 - 2 b_j1 )^2
                      </div>
                      <p className="text-[11px] text-[#8f8b8a]">
                        Where x_i in {"{0, 1}"} selects waypoint i, A_ji in {"{0, 1}"} represents coverage, k is required redundancy, and b_j0, b_j1 are binary slack bits. The default penalty coefficient lambda = 7.0 ensures ground states strictly satisfy k-coverage.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 2: 4-Solver Benchmark Comparison */}
        {activeTab === 'benchmark' && (
          <div className="p-6 rounded-2xl bg-white/90 backdrop-blur-md border border-[#e2dedd] shadow-sm space-y-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-[#e2dedd] pb-4">
              <div>
                <h3 className="font-bold text-xl text-[#141516]">
                  Direct Classical vs Quantum Solver Benchmark
                </h3>
                <p className="text-[#8f8b8a] text-xs font-mono mt-0.5">
                  Scenario: {compareResults?.scenario_name || scenarioDetail?.name}
                </p>
              </div>

              <button
                type="button"
                onClick={handleRunComparison}
                disabled={comparing}
                className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-mono text-xs font-bold tracking-wider transition-all flex items-center gap-2 shadow-sm"
              >
                {comparing ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>BENCHMARKING...</span>
                  </>
                ) : (
                  <>
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>RE-RUN COMPARISON</span>
                  </>
                )}
              </button>
            </div>

            {compareResults ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left font-mono text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-[#e2dedd] text-[#8f8b8a] bg-[#F7F5EF]">
                      <th className="py-3 px-4">SOLVER</th>
                      <th className="py-3 px-4">TYPE</th>
                      <th className="py-3 px-4">FEASIBLE</th>
                      <th className="py-3 px-4">SELECTED WAYPOINTS</th>
                      <th className="py-3 px-4">WAYPOINT COUNT</th>
                      <th className="py-3 px-4">RUNTIME</th>
                      <th className="py-3 px-4">OPTIMALITY GAP</th>
                      <th className="py-3 px-4">SAMPLING YIELD</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#e2dedd]">
                    {compareResults.results.map((res) => {
                      const isQuantum = res.solver.name.toLowerCase() === 'qaoa';
                      return (
                        <tr key={res.run_id} className={`hover:bg-slate-50 transition-colors ${isQuantum ? 'bg-emerald-50/40' : ''}`}>
                          <td className="py-3 px-4 font-bold text-[#141516] flex items-center gap-2">
                            {isQuantum && <Cpu className="w-3.5 h-3.5 text-emerald-600" />}
                            <span>{res.solver.name.toUpperCase()}</span>
                          </td>
                          <td className="py-3 px-4 text-[#8f8b8a]">
                            {isQuantum ? 'Quantum (QAOA)' : 'Classical'}
                          </td>
                          <td className="py-3 px-4">
                            <span
                              className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                                res.result.feasible
                                  ? 'bg-emerald-100 text-emerald-800'
                                  : 'bg-rose-100 text-rose-800'
                              }`}
                            >
                              {res.result.feasible ? 'FEASIBLE' : 'INFEASIBLE'}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-[#141516]">
                            [{res.result.selected_waypoint_ids.join(', ')}]
                          </td>
                          <td className="py-3 px-4 font-bold text-[#141516]">
                            {res.result.selected_waypoint_count}
                          </td>
                          <td className="py-3 px-4 text-emerald-700 font-bold">
                            {(res.result.runtime_seconds * 1000).toFixed(1)} ms
                          </td>
                          <td className="py-3 px-4 text-[#141516]">
                            {res.metadata.optimality_gap !== undefined && res.metadata.optimality_gap !== null
                              ? res.metadata.optimality_gap.toFixed(2)
                              : '0.00'}
                          </td>
                          <td className="py-3 px-4 text-[#8f8b8a]">
                            {isQuantum && res.metadata.feasible_rate !== undefined
                              ? `Feasible Rate: ${(Number(res.metadata.feasible_rate) * 100).toFixed(1)}%`
                              : '100% (Deterministic)'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="py-12 text-center text-[#8f8b8a] font-mono text-sm">
                Click &quot;Run Multi-Solver Benchmark&quot; to execute all 4 solvers side-by-side.
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Historical Optimization Runs */}
        {activeTab === 'history' && (
          <div className="p-6 rounded-2xl bg-white/90 backdrop-blur-md border border-[#e2dedd] shadow-sm space-y-6">
            <div className="flex items-center justify-between border-b border-[#e2dedd] pb-4">
              <div>
                <h3 className="font-bold text-xl text-[#141516]">
                  Experiment Optimization History
                </h3>
                <p className="text-[#8f8b8a] text-xs font-mono mt-0.5">
                  Persisted SQLite/PostgreSQL optimization runs recorded by the FastAPI backend.
                </p>
              </div>

              <button
                type="button"
                onClick={loadHistory}
                disabled={loadingHistory}
                className="p-2 rounded-lg bg-[#F7F5EF] hover:bg-slate-200 border border-[#e2dedd] text-[#141516] transition-colors"
                title="Refresh history"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
            </div>

            {loadingHistory ? (
              <div className="py-12 text-center text-[#8f8b8a] font-mono text-sm">
                Loading history from database...
              </div>
            ) : historyItems.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left font-mono text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-[#e2dedd] text-[#8f8b8a] bg-[#F7F5EF]">
                      <th className="py-3 px-4">RUN ID</th>
                      <th className="py-3 px-4">TIMESTAMP</th>
                      <th className="py-3 px-4">SCENARIO</th>
                      <th className="py-3 px-4">SOLVER</th>
                      <th className="py-3 px-4">STATUS</th>
                      <th className="py-3 px-4">WAYPOINTS</th>
                      <th className="py-3 px-4">RUNTIME</th>
                      <th className="py-3 px-4">ACTION</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#e2dedd]">
                    {historyItems.map((item) => (
                      <tr key={item.id} className="hover:bg-slate-50 transition-colors">
                        <td className="py-3 px-4 text-emerald-700 font-bold">{item.run_id.slice(0, 8)}...</td>
                        <td className="py-3 px-4 text-[#8f8b8a]">{item.created_at.slice(0, 19).replace('T', ' ')}</td>
                        <td className="py-3 px-4 text-[#141516]">{item.scenario_name}</td>
                        <td className="py-3 px-4 uppercase text-[#141516] font-bold">{item.solver_name}</td>
                        <td className="py-3 px-4">
                          <span
                            className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                              item.feasible
                                ? 'bg-emerald-100 text-emerald-800'
                                : 'bg-rose-100 text-rose-800'
                            }`}
                          >
                            {item.status}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-[#141516]">{item.selected_waypoint_count ?? 'N/A'}</td>
                        <td className="py-3 px-4 text-emerald-700">
                          {item.runtime_seconds !== null && item.runtime_seconds !== undefined
                            ? `${(item.runtime_seconds * 1000).toFixed(1)} ms`
                            : 'N/A'}
                        </td>
                        <td className="py-3 px-4">
                          <button
                            type="button"
                            onClick={() => handleSelectHistoryRun(item.run_id)}
                            className="px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 border border-[#e2dedd] text-[#141516] font-bold transition-colors"
                          >
                            LOAD
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="py-12 text-center text-[#8f8b8a] font-mono text-sm">
                No past optimization runs recorded yet. Execute an optimization above to populate database history.
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
};
