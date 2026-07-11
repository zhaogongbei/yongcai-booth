import type { PrinterInfo } from "../../lib/api";

const EXCLUDED_PRINTER_NAMES = new Set([
  "GE801PN",
  "GE801PN-Test",
  "GE801PN-DriverTest",
  "导出为WPS PDF",
  "Microsoft Print to PDF",
]);

export function isPreferredPrinter(printer: PrinterInfo, preferredName?: string): boolean {
  return Boolean(preferredName) && printer.name === preferredName;
}

export function isExcludedPrinter(printer: PrinterInfo): boolean {
  return EXCLUDED_PRINTER_NAMES.has(printer.name);
}

export function isVirtualPrinter(printer: PrinterInfo): boolean {
  const driver = (printer.driver_name ?? "").toLowerCase();
  const port = (printer.port_name ?? "").toUpperCase();
  const name = printer.name.toLowerCase();

  return (
    name.includes("pdf") ||
    driver.includes("pdf") ||
    driver.includes("virtual") ||
    port === "PORTPROMPT:"
  );
}

export function isSupportedBoothPrinter(printer: PrinterInfo, preferredName?: string): boolean {
  if (isPreferredPrinter(printer, preferredName)) return true;
  if (isExcludedPrinter(printer) || isVirtualPrinter(printer)) return false;
  return true;
}

export function getBoothPrinters(printers: PrinterInfo[], preferredName?: string): PrinterInfo[] {
  return [...printers]
    .filter((printer) => isSupportedBoothPrinter(printer, preferredName))
    .sort((left, right) => {
      if (isPreferredPrinter(left, preferredName)) return -1;
      if (isPreferredPrinter(right, preferredName)) return 1;
      if (left.status === "ready" && right.status !== "ready") return -1;
      if (left.status !== "ready" && right.status === "ready") return 1;
      return left.name.localeCompare(right.name, "zh-CN");
    });
}

export function getDefaultBoothPrinter(printers: PrinterInfo[], preferredName?: string): PrinterInfo | undefined {
  const supported = getBoothPrinters(printers, preferredName);
  return supported.find((printer) => isPreferredPrinter(printer, preferredName))
    ?? supported.find((printer) => printer.is_default)
    ?? supported[0];
}
