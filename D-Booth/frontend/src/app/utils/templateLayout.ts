import type { PhotoElementProps, TemplateLayout } from "../types/template";

export function hasPrintablePhotoFrame(layout: TemplateLayout | null | undefined): boolean {
  if (!layout) return false;

  return layout.elements.some(element => {
    if (!element.visible || element.type !== "photo") return false;
    const photoNumber = Number((element.props as Partial<PhotoElementProps>).photoNumber);
    return Number.isFinite(photoNumber) && photoNumber >= 1;
  });
}

export function getRequiredTemplatePhotoCount(layout: TemplateLayout | null | undefined): number {
  if (!layout) return 0;

  return layout.elements.reduce((required, element) => {
    if (!element.visible || element.type !== "photo") return required;
    const photoNumber = Number((element.props as Partial<PhotoElementProps>).photoNumber);
    if (!Number.isFinite(photoNumber) || photoNumber < 1) return required;
    return Math.max(required, Math.floor(photoNumber));
  }, 0);
}

export function getTemplatePhotoSlots(layout: TemplateLayout | null | undefined): number[] {
  const requiredCount = getRequiredTemplatePhotoCount(layout);
  return Array.from({ length: requiredCount }, (_, index) => index + 1);
}
