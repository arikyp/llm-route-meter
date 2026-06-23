export declare function fingerprintText(value: string, salt?: string): string;
export declare function findForbiddenKeys(value: unknown, path?: string): string[];
export declare function assertMetadataOnly(event: Record<string, unknown>): void;
export declare class LocalMeterWriter {
  constructor(path: string);
  writeEvent(event: Record<string, unknown>): void;
}
export declare function meteredCall<T>(params: {
  routeId: string;
  model: string;
  writer: LocalMeterWriter;
  provider?: string;
  environment?: string;
  batchable?: boolean;
  qualitySignal?: string;
  templateFingerprint?: string;
  toolSchemaFingerprint?: string;
  call: () => Promise<T>;
}): Promise<T>;
