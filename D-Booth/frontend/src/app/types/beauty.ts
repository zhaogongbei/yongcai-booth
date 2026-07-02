/**
 * Beauty related types
 */
export interface BeautyParams {
  smooth: number;
  whiten: number;
  thinFace: number;
  bigEye: number;
  eyeLight: number;
  acne: number;
  nasolabial: number;
  teethWhiten: number;
  lipColor: number;
}

export interface BeautyPreset {
  name: string;
  params: BeautyParams;
}

export interface FaceBox {
  x: number;
  y: number;
  width: number;
  height: number;
  confidence: number;
  landmark_count: number;
}

export interface FaceDetectionResponse {
  face_count: number;
  faces: FaceBox[];
}
