import type { PrinterInfo } from "../../lib/api";

export const PREFERRED_PRINTER_NAME = "HP LaserJet Professional P1108";

const EXCLUDED_PRINTER_NAMES = new Set([
  "GE801PN",
  "GE801PN-Test",
  "GE801PN-DriverTest",
  "导出为WPS PDF",
  "Microsoft Print to PDF",
]);

export function isPreferredPrinter(printer: PrinterInfo): boolean {
  return printer.name === PREFERRED_PRINTER_NAME;
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

export function isSupportedBoothPrinter(printer: PrinterInfo): boolean {
  if (isPreferredPrinter(printer)) return true;
  if (isExcludedPrinter(printer) || isVirtualPrinter(printer)) return false;
  return true;
}

export function getBoothPrinters(printers: PrinterInfo[]): PrinterInfo[] {
  return [...printers]
    .filter(isSupportedBoothPrinter)
    .sort((left, right) => {
      if (isPreferredPrinter(left)) return -1;
      if (isPreferredPrinter(right)) return 1;
      if (left.status === "ready" && right.status !== "ready") return -1;
      if (left.status !== "ready" && right.status === "ready") return 1;
      return left.name.localeCompare(right.name, "zh-CN");
    });
}

export function getDefaultBoothPrinter(printers: PrinterInfo[]): PrinterInfo | undefined {
  const supported = getBoothPrinters(printers);
  return supported.find(isPreferredPrinter) ?? supported.find((printer) => printer.is_default) ?? supported[0];
}
