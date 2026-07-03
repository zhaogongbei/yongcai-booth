import { onCLS, onINP, onLCP, onFCP, onTTFB } from 'web-vitals';
import { resolveBackendUrl } from '@/lib/api';

type MetricRating = 'good' | 'needs-improvement' | 'poor';

interface MetricReport {
  name: string;
  value: number;
  rating: MetricRating;
  delta: number;
  id: string;
  navigationType: 'navigate' | 'reload' | 'back-forward' | 'prerender';
}

const WEB_VITALS_ENDPOINT = import.meta.env.VITE_WEB_VITALS_ENDPOINT?.trim();

function getRating(name: string, value: number): MetricRating {
  switch (name) {
    case 'LCP':
      return value <= 2500 ? 'good' : value <= 4000 ? 'needs-improvement' : 'poor';
    case 'INP':
      return value <= 100 ? 'good' : value <= 300 ? 'needs-improvement' : 'poor';
    case 'CLS':
      return value <= 0.1 ? 'good' : value <= 0.25 ? 'needs-improvement' : 'poor';
    case 'FCP':
      return value <= 1800 ? 'good' : value <= 3000 ? 'needs-improvement' : 'poor';
    case 'TTFB':
      return value <= 800 ? 'good' : value <= 1800 ? 'needs-improvement' : 'poor';
    default:
      return 'good';
  }
}

function reportMetric(metric: MetricReport): void {
  // Log to console in development
  if (import.meta.env.DEV) {
    console.log(`[Web Vital] ${metric.name}: ${metric.value} (${metric.rating})`);
  }

  if (navigator.onLine && import.meta.env.PROD && WEB_VITALS_ENDPOINT) {
    fetch(resolveBackendUrl(WEB_VITALS_ENDPOINT), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: metric.name,
        value: metric.value,
        rating: metric.rating,
        delta: metric.delta,
        id: metric.id,
        navigationType: metric.navigationType,
        timestamp: Date.now(),
      }),
      keepalive: true,
    }).catch(() => {
      // Silently fail if analytics endpoint is not available
    });
  }
}

function sendToAnalytics(metric: any): void {
  const report: MetricReport = {
    name: metric.name,
    value: Math.round(metric.name === 'CLS' ? metric.value * 1000 : metric.value),
    rating: getRating(metric.name, metric.value),
    delta: Math.round(metric.delta),
    id: metric.id,
    navigationType: metric.navigationType,
  };
  reportMetric(report);
}

export function initPerformanceMonitoring(): void {
  // Only run in supported browsers
  if (typeof window === 'undefined') return;

  // Report all Web Vitals
  try {
    onCLS(sendToAnalytics);
    onINP(sendToAnalytics);
    onLCP(sendToAnalytics);
    onFCP(sendToAnalytics);
    onTTFB(sendToAnalytics);
  } catch (error) {
    console.warn('Web Vitals monitoring not supported:', error);
  }

  // Log long tasks (> 50ms)
  if ('PerformanceObserver' in window) {
    try {
      const observer = new PerformanceObserver((list) => {
        list.getEntries().forEach((entry) => {
          if (entry.duration > 50) {
            console.debug(`Long task detected: ${entry.duration.toFixed(2)}ms`, entry);
          }
        });
      });
      observer.observe({ type: 'longtask', buffered: true });
    } catch (error) {
      // Long task observer not supported in all browsers
    }
  }
}

// Navigation timing stats
export function getNavigationTiming(): PerformanceNavigationTiming | null {
  const entries = performance.getEntriesByType('navigation') as PerformanceNavigationTiming[];
  return entries.length > 0 ? entries[0] : null;
}
