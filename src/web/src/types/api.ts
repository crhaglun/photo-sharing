export interface PagedResponse<T> {
  items: T[];
  page: number;
  pageSize: number;
  totalCount: number;
  totalPages: number;
}

export interface PhotoSummary {
  id: string;
  originalFilename: string;
  dateNotEarlierThan: string | null;
  dateNotLaterThan: string | null;
  placeName: string | null;
  isLowQuality: boolean;
  faceCount: number;
}

export interface PhotoListParams {
  dateStart?: string;
  dateEnd?: string;
  placeId?: string;
  personId?: string;
  includeLowQuality?: boolean;
  page?: number;
  pageSize?: number;
}

export interface PhotoDetail {
  id: string;
  originalFilename: string;
  dateNotEarlierThan: string | null;
  dateNotLaterThan: string | null;
  isLowQuality: boolean;
  createdAt: string;
  updatedAt: string;
  place: PlaceResponse | null;
  exif: ExifResponse | null;
  faces: FaceInPhotoResponse[];
  editHistory: EditHistoryResponse[];
}

export interface PlaceResponse {
  id: string;
  nameSv: string;
  nameEn: string;
  type: string;
  parent: PlaceResponse | null;
}

export interface ExifResponse {
  cameraMake: string | null;
  cameraModel: string | null;
  lens: string | null;
  focalLength: string | null;
  aperture: string | null;
  shutterSpeed: string | null;
  iso: number | null;
  takenAt: string | null;
}

export interface FaceInPhotoResponse {
  id: string;
  personId: string | null;
  personName: string | null;
  clusterId: string | null;
  bboxX: number;
  bboxY: number;
  bboxWidth: number;
  bboxHeight: number;
}

export interface EditHistoryResponse {
  fieldType: string;
  fieldKey: string;
  oldValue: string | null;
  newValue: string | null;
  changedBy: string;
  changedAt: string;
}

export interface PersonResponse {
  id: string;
  name: string;
  faceCount: number;
  createdAt: string;
}

export interface ApiError {
  status: number;
  message: string;
}

export interface FaceCluster {
  clusterId: string;
  faces: FaceInCluster[];
}

export interface FaceInCluster {
  id: string;
  photoId: string;
  bboxX: number;
  bboxY: number;
  bboxWidth: number;
  bboxHeight: number;
}

export interface Place {
  id: string;
  nameSv: string;
  nameEn: string;
  type: string;
  parentId: string | null;
}

export interface DateRange {
  minDate: string | null;
  maxDate: string | null;
}
