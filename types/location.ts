// types/location.ts
export interface Location {
  id: string;
  city: string;
  inhabitants: number;
  populationGrowth: number;
  description: string;
  investmentHighlights: string[];
  employers: Employer[];
  images: LocationImage[];
}

export interface Employer {
  id: string;
  name: string;
  description: string;
  employees: number;
}

export interface LocationImage {
  id: string;
  url: string;
  alt: string;
  category: string;
}