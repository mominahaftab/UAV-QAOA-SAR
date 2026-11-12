/**
 * Frontend TypeScript interfaces for UAV-QAOA-SAR.
 * Perfectly aligned with backend Pydantic DTO schemas and RF link-budget simulation.
 */

export interface TargetPoint {
  id: string;
  x: number;
  y: number;
  height_m?: number;
  priority?: number;
}

export interface WaypointPoint {
  id: string;
  x: number;
  y: number;
  altitude_m?: number;
  cost?: number;
}

export interface RFConfigDTO {
  frequency_mhz: number;
  tx_power_dbm: number;
  tx_antenna_gain_dbi: number;
  rx_antenna_gain_dbi: number;
  rx_sensitivity_dbm: number;
  system_loss_db: number;
  fade_margin_db: number;
  environment: 'open' | 'suburban' | 'urban' | string;
  excess_loss_db?: number | null;
  uav_altitude_m: number;
  target_height_m: number;
}

export interface RFLinkResultDTO {
  target_id: string;
  waypoint_id: string;
  distance_3d_m: number;
  distance_km: number;
  fspl_db: number;
  received_power_dbm: number;
  threshold_dbm: number;
  link_margin_db: number;
  is_covered: boolean;
}

export interface ScenarioSummaryDTO {
  id: string;
  name: string;
  target_count: number;
  waypoint_count: number;
  k_coverage: number;
  description: string;
  scenario_type?: 'synthetic' | 'rf_simulation' | string;
}

export interface ScenarioDetailDTO {
  id: string;
  name: string;
  target_ids: string[];
  waypoint_ids: string[];
  coverage_matrix: number[][];
  k_coverage: number;
  targets?: TargetPoint[];
  waypoints?: WaypointPoint[];
  rf_config?: RFConfigDTO | null;
  rf_links?: RFLinkResultDTO[] | null;
  scenario_type?: 'synthetic' | 'rf_simulation' | string;
}

export interface RFSimulationRequestDTO {
  scenario_name?: string;
  rf_config: RFConfigDTO;
  k_coverage?: number;
  targets?: TargetPoint[];
  waypoints?: WaypointPoint[];
}

export interface RFSimulationResponseDTO {
  scenario_name: string;
  rf_config: RFConfigDTO;
  k_coverage: number;
  target_ids: string[];
  waypoint_ids: string[];
  coverage_matrix: number[][];
  coverage_counts: Record<string, number>;
  unsatisfied_targets: string[];
  is_feasible: boolean;
  links: RFLinkResultDTO[];
  targets: TargetPoint[];
  waypoints: WaypointPoint[];
}

export type SolverName = 'qaoa' | 'milp' | 'brute_force' | 'greedy';

export interface OptimizeRequestDTO {
  scenario_id?: string;
  target_ids?: string[];
  waypoint_ids?: string[];
  coverage_matrix?: number[][];
  k_coverage?: number;
  solver_name: SolverName | string;
  qaoa_depth?: number;
  shots?: number;
  penalty?: number;
  max_iterations?: number;
  random_seed?: number;
  rf_config?: RFConfigDTO | null;
}

export interface OptimizeResultDetails {
  selected_waypoint_ids: string[];
  selected_waypoint_count: number;
  coverage_counts: Record<string, number>;
  feasible: boolean;
  objective_value: number;
  runtime_seconds: number;
}

export interface OptimizationResponseDTO {
  run_id: string;
  status: 'completed' | 'no_feasible_solution' | 'failed' | string;
  scenario: {
    id?: string;
    name?: string;
    target_count?: number;
    waypoint_count?: number;
    k_coverage?: number;
    [key: string]: unknown;
  };
  solver: {
    name: string;
    type?: string;
    parameters?: Record<string, unknown>;
    [key: string]: unknown;
  };
  result: OptimizeResultDetails;
  metadata: {
    feasible_sampling_probability?: number;
    iterations_used?: number;
    optimal_gamma?: number[];
    optimal_beta?: number[];
    num_qubits?: number;
    p?: number;
    shots?: number;
    penalty?: number;
    optimality_gap?: number | null;
    [key: string]: unknown;
  };
}

export interface CompareRequestDTO {
  scenario_id?: string;
  target_ids?: string[];
  waypoint_ids?: string[];
  coverage_matrix?: number[][];
  k_coverage?: number;
  solvers?: string[];
  qaoa_options?: {
    qaoa_depth?: number;
    shots?: number;
    penalty?: number;
    max_iterations?: number;
    random_seed?: number;
  };
  rf_config?: RFConfigDTO | null;
}

export interface CompareResponseDTO {
  scenario_name: string;
  results: OptimizationResponseDTO[];
}

export interface HistoryItemDTO {
  id: number;
  run_id: string;
  created_at: string;
  scenario_name: string;
  solver_name: string;
  status: string;
  feasible?: boolean | null;
  selected_waypoint_count?: number | null;
  objective_value?: number | null;
  runtime_seconds?: number | null;
}

export interface HistoryListDTO {
  items: HistoryItemDTO[];
  total: number;
  limit: number;
  offset: number;
}

export interface HistoryDetailDTO {
  id: number;
  run_id: string;
  created_at: string;
  scenario_name: string;
  solver_name: string;
  status: string;
  request_data: Record<string, unknown>;
  result_data: Record<string, unknown>;
  selected_waypoint_count?: number | null;
  feasible?: boolean | null;
  objective_value?: number | null;
  runtime_seconds?: number | null;
  error_message?: string | null;
}
