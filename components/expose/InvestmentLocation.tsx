// components/expose/InvestmentLocation.tsx
import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { CheckCircle2 } from 'lucide-react';

interface InvestmentLocationProps {
  location: {
    city: string;
    description: string;
    investmentHighlights: string[];
    images: Array<{ url: string; alt: string; category: string }>;
  };
}

export default function InvestmentLocation({ location }: InvestmentLocationProps) {
  const cityImage = location.images.find(img => img.category === 'city') || location.images[0];

  return (
    <div className="py-16 px-6 md:px-12 lg:px-20 bg-white">
      <div className="container mx-auto max-w-6xl">
        <div className="grid lg:grid-cols-2 gap-12 items-start">
          {/* Left Content */}
          <div>
            <h2 className="text-4xl font-bold mb-2">Investitionsstandort</h2>
            <h3 className="text-3xl font-bold mb-8 text-invenio-gold uppercase">{location.city}</h3>
            
            <div className="space-y-6">
              {location.investmentHighlights.map((highlight, index) => (
                <div key={index} className="pb-6 border-b last:border-0">
                  <h4 className="font-bold text-lg mb-2 flex items-center gap-2">
                    <span className="text-invenio-gold">{index + 1}.</span>
                    {highlight.split('\n')[0]}
                  </h4>
                  <p className="text-gray-700 leading-relaxed">
                    {highlight.split('\n').slice(1).join('\n')}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Right Image */}
          <div className="relative">
            <div className="sticky top-8">
              <div className="relative aspect-[4/3] rounded-lg overflow-hidden shadow-2xl">
                <img
                  src={cityImage?.url || '/images/nuremberg-aerial.jpg'}
                  alt={cityImage?.alt || `${location.city} Stadtansicht`}
                  className="w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/30 to-transparent" />
              </div>
              
              {/* Investment Badge */}
              <div className="absolute -bottom-6 -right-6 bg-invenio-gold text-white p-6 rounded-full shadow-xl">
                <div className="text-center">
                  <p className="text-xs font-semibold">TOP</p>
                  <p className="text-2xl font-bold">A</p>
                  <p className="text-xs font-semibold">LAGE</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}