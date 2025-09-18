import { useEffect, useRef } from 'react';
import { apiClient } from '@/services/api';
import type { NodeTelemetryPoint } from '@/types';

export const useLiveTelemetry = (
  orgId: string | undefined,
  onTelemetry: (payload: NodeTelemetryPoint) => void
) => {
  const callbackRef = useRef(onTelemetry);

  useEffect(() => {
    callbackRef.current = onTelemetry;
  }, [onTelemetry]);

  useEffect(() => {
    if (!orgId) return;
    const unsubscribe = apiClient.subscribeToLive(orgId, (payload) => {
      callbackRef.current(payload);
    });

    return () => {
      unsubscribe?.();
    };
  }, [orgId]);
};
