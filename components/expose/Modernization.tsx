// components/expose/Modernization.tsx
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Hammer, CheckCircle, Sparkles } from 'lucide-react';

interface ModernizationProps {
  modernizationDetails: string[];
}

export default function Modernization({ modernizationDetails }: ModernizationProps) {
  return (
    <div className="py-16 px-6 md:px-12 lg:px-20 bg-gray-50">
      <div className="container mx-auto max-w-6xl">
        <div className="grid lg:grid-cols-2 gap-12 items-start">
          {/* Left Content */}
          <div>
            <h2 className="text-4xl font-bold mb-8">MODERNISIERUNG</h2>
            
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Hammer className="w-5 h-5 text-invenio-gold" />
                  Auszuführende Arbeiten sind insbesondere dabei:
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3">
                  {modernizationDetails.map((detail, index) => (
                    <li key={index} className="flex items-start gap-3">
                      <CheckCircle className="w-5 h-5 text-green-600 mt-0.5 flex-shrink-0" />
                      <span className="text-gray-700">{detail}</span>
                    </li>
                  ))}
                </ul>
                
                <div className="mt-8 p-4 bg-invenio-beige/30 rounded-lg">
                  <p className="text-sm text-gray-700 italic">
                    Alle Arbeiten werden im gehobenen Standard durchgeführt. 
                    Alle Angaben werden im Kaufvertrag festgehalten und die 
                    Angaben im Kaufvertrag sind verbindlich.
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Right Image */}
          <div className="relative">
            <div className="sticky top-8">
              <div className="relative aspect-[4/3] rounded-lg overflow-hidden shadow-2xl">
                <img
                  src="/images/modern-apartment.jpg"
                  alt="Modernisierte Wohnung"
                  className="w-full h-full object-cover"
                />
                <div className="absolute top-4 right-4 bg-white/90 backdrop-blur px-4 py-2 rounded-full shadow-lg">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-invenio-gold" />
                    <span className="font-semibold">Gehobener Standard</span>
                  </div>
                </div>
              </div>

              {/* Floor Plan Preview */}
              <Card className="mt-6">
                <CardContent className="p-4">
                  <h4 className="font-semibold mb-3">Grundrissoptimierung</h4>
                  <div className="bg-gray-100 rounded p-4">
                    <img
                      src="/images/floor-plan.png"
                      alt="Grundriss"
                      className="w-full"
                    />
                  </div>
                  <p className="text-sm text-gray-600 mt-3">
                    Optimierung zur 4-Zimmer WG-Wohnung
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}