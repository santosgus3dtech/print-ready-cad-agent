export type Template = 'enclosure' | 'bracket' | 'adapter';
export interface Parameters {
  width: number; depth: number; height: number; wall: number; clearance: number;
  hole_diameter: number; inner_diameter: number; outer_diameter: number; base_thickness: number;
}
export interface Spec {
  template: Template; printer: 'bambu-a1' | 'creality-k1c';
  material: 'PLA' | 'PETG' | 'ABS'; nozzle: 0.2 | 0.4 | 0.6 | 0.8; parameters: Parameters;
}
export interface Evidence { id: string; title: string; text: string; score: number }
export interface Check { id: string; label: string; status: 'pass' | 'warning' | 'fail'; detail: string }
export interface SlicerResult {
  status: string; detail?: string; printer_profile?: string; process_profile?: string;
  filament_profile?: string; time?: string; filament_g?: number; warnings?: string[];
}
export interface Job {
  id: string; created_at: string; spec: Spec; duration_ms: number; evidence: Evidence[];
  artifacts: Record<string, {url: string; bytes?: number; sha256?: string}>;
  report: {
    status: string; checks: Check[]; components: number; volume_mm3: number; dimensions: number[];
    warnings: string[]; scope: string;
    parts: { name: string; dimensions: number[]; volume_mm3: number; shells: number }[];
  };
  slicer: SlicerResult;
}
export const NAMES: Record<Template, string> = {
  enclosure: 'Electronics enclosure', bracket: 'Mounting bracket', adapter: 'Flanged adapter',
};
