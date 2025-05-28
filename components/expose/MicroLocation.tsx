// components/expose/MicroLocation.tsx
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { MapPin, ShoppingBag, Coffee, Train, Bus, Building } from 'lucide-react';

interface MicroLocationProps {
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

export default function MicroLocation({ microLocation }: MicroLocationProps) {
  return (
    <div className="py-16 px-6 md:px-12 lg:px-20 bg-white">
      <div className="container mx-auto max-w-6xl">
        <h2 className="text-4xl font-bold mb-8">MICROLAGE</h2>

        <div className="grid lg:grid-cols-3 gap-8 mb-12">
          {/* Leisure */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Coffee className="w-5 h-5 text-invenio-gold" />
                Freizeitmöglichkeiten
              </CardTitle>
              <p className="text-sm text-gray-600">Innerhalb von 5-20 Minuten erreichbar:</p>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2">
                {microLocation.leisure.map((item, index) => (
                  <li key={index} className="flex items-start gap-2">
                    <span className="text-invenio-gold mt-1">•</span>
                    <span className="text-gray-700">{item}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          {/* Shopping */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ShoppingBag className="w-5 h-5 text-invenio-gold" />
                Einkaufsmöglichkeiten
              </CardTitle>
              <p className="text-sm text-gray-600">Innerhalb von 5-15 Minuten erreichbar:</p>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2">
                {microLocation.shopping.map((item, index) => (
                  <li key={index} className="flex items-start gap-2">
                    <span className="text-invenio-gold mt-1">•</span>
                    <span className="text-gray-700">{item}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          {/* Infrastructure */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MapPin className="w-5 h-5 text-invenio-gold" />
                Infrastruktur
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center gap-3">
                <Train className="w-5 h-5 text-gray-600" />
                <div>
                  <p className="text-sm text-gray-600">U-Bahn</p>
                  <p className="font-semibold">{microLocation.infrastructure.uBahn}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Bus className="w-5 h-5 text-gray-600" />
                <div>
                  <p className="text-sm text-gray-600">Bus</p>
                  <p className="font-semibold">{microLocation.infrastructure.bus}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Building className="w-5 h-5 text-gray-600" />
                <div>
                  <p className="text-sm text-gray-600">Zentrum</p>
                  <p className="font-semibold">{microLocation.infrastructure.cityCenter}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Map */}
        <Card className="overflow-hidden">
          <div className="relative h-96 bg-gray-100">
            <img
              src="/images/microlocation-map.jpg"
              alt="Mikrolage Karte"
              className="w-full h-full object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent" />
            <div className="absolute bottom-4 left-4 right-4 text-white">
              <div className="bg-blue-600 inline-flex items-center gap-2 px-4 py-2 rounded-full shadow-lg">
                <div className="w-3 h-3 bg-white rounded-full animate-pulse" />
                <span className="font-semibold">Hintermayrstr. 3a</span>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}