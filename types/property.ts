// types/property.ts
export interface Property {
  id: string;
  unitNumber: number;
  district: string;
  rooms: number;
  buildingYear: number;
  lastModernization: number;
  size: number;
  floor: string;
  totalUnits: number;
  totalFloors: string;
  hasBasement: boolean;
  hasBalcony: boolean;
  heatingType: string;
  energyCarrier: string;
  energyConsumption: string;
  hasElevator: boolean;
  depreciation: number;
  reserves: number;
  monthlyRent: {
    room1: number;
    room2: number;
    room3: number;
    room4: number;
  };
  purchasePrice: number;
  purchaseCosts: number;
  modernizationDetails: string[];
  microLocation: {
    leisure: string[];
    shopping: string[];
    infrastructure: {
      uBahn: string;
      bus: string;
      cityCenter: string;
    };
  };
}