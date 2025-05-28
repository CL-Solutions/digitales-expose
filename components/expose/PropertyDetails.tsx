// components/expose/PropertyDetails.tsx
import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { 
  Home, Calendar, Ruler, Layers, Thermometer, 
  Building, Euro, Users, Wrench, Archive 
} from 'lucide-react';

interface PropertyDetailsProps {
  property: {
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
  };
}

export default function PropertyDetails({ property }: PropertyDetailsProps) {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('de-DE', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const details = [
    { icon: Home, label: 'Wohneinheit', value: property.unitNumber },
    { icon: Building, label: 'Stadtteil', value: property.district },
    { icon: Users, label: 'Zimmeranzahl', value: property.rooms },
    { icon: Calendar, label: 'Baujahr', value: property.buildingYear },
    { icon: Wrench, label: 'Letzte Modernisierung', value: property.lastModernization },
    { icon: Ruler, label: 'Mietfläche', value: `ca. ${property.size} qm` },
    { icon: Layers, label: 'Lage im Gebäude', value: property.floor },
    { icon: Building, label: 'Gesamtanzahl Wohneinheiten', value: property.totalUnits },
    { icon: Layers, label: 'Gesamtanzahl Etagen', value: property.totalFloors },
    { icon: Archive, label: 'Keller', value: property.hasBasement ? 'vorhanden' : 'nicht vorhanden' },
    { icon: Home, label: 'Balkon', value: property.hasBalcony ? 'vorhanden' : 'nicht vorhanden' },
    { icon: Thermometer, label: 'Energieträger', value: property.heatingType },
  ];

  return (
    <div className="py-16 px-6 md:px-12 lg:px-20 bg-white">
      <div className="container mx-auto max-w-6xl">
        <h2 className="text-4xl font-bold mb-2">Objekt</h2>
        <p className="text-xl text-gray-600 mb-8">DATEN</p>

        <div className="grid lg:grid-cols-2 gap-8">
          {/* Property Details Table */}
          <Card>
            <CardContent className="p-0">
              <table className="w-full">
                <tbody>
                  {details.map((detail, index) => (
                    <tr key={index} className="border-b last:border-0">
                      <td className="p-4 font-medium text-gray-700">{detail.label}</td>
                      <td className="p-4 text-right">{detail.value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>

          {/* Additional Info */}
          <div className="space-y-6">
            {/* Rental Income */}
            <Card className="bg-invenio-beige/20">
              <CardContent className="p-6">
                <h3 className="font-semibold mb-4 flex items-center gap-2">
                  <Euro className="w-5 h-5" />
                  Vermietung
                </h3>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span>Zimmer 1:</span>
                    <span className="font-semibold">{formatCurrency(property.monthlyRent.room1)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Zimmer 2:</span>
                    <span className="font-semibold">{formatCurrency(property.monthlyRent.room2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Zimmer 3:</span>
                    <span className="font-semibold">{formatCurrency(property.monthlyRent.room3)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Zimmer 4:</span>
                    <span className="font-semibold">{formatCurrency(property.monthlyRent.room4)}</span>
                  </div>
                  <div className="border-t pt-2 mt-2">
                    <div className="flex justify-between font-bold">
                      <span>Gesamt:</span>
                      <span className="text-green-600">
                        {formatCurrency(
                          property.monthlyRent.room1 + 
                          property.monthlyRent.room2 + 
                          property.monthlyRent.room3 + 
                          property.monthlyRent.room4
                        )}
                      </span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Financial Info */}
            <Card>
              <CardContent className="p-6">
                <h3 className="font-semibold mb-4">Weitere Informationen</h3>
                <div className="space-y-3">
                  <div>
                    <p className="text-sm text-gray-600">Energieverbrauch</p>
                    <p className="font-semibold">{property.energyConsumption}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Aufzug</p>
                    <p className="font-semibold">{property.hasElevator ? 'vorhanden' : 'nicht vorhanden'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Abschreibung</p>
                    <p className="font-semibold">{property.depreciation}%</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Enthaltungsrücklagen</p>
                    <p className="font-semibold">{formatCurrency(property.reserves)}</p>
                    <p className="text-xs text-gray-500">(Stand 31.12.2023)</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Community Property */}
            <Card>
              <CardContent className="p-6">
                <h3 className="font-semibold mb-4">Gemeinschaftseigentum</h3>
                <ul className="space-y-2 text-sm">
                  <li>• 2024: Neue Gaszentralheizung</li>
                  <li>• 2022: Modernisierung Aufzug</li>
                  <li>• 2018: Sanierung des Daches</li>
                  <li>• ca. 2010: Kunststoffisolierglas</li>
                </ul>
                <p className="mt-4 text-sm text-gray-600">
                  Sonderumlagen werden die nächsten zwei Jahre übernommen
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}