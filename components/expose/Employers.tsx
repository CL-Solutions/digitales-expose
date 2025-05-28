// components/expose/Employers.tsx
import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Building2, Users, MapPin } from 'lucide-react';

interface Employer {
  id: string;
  name: string;
  description: string;
  employees: number;
}

interface EmployersProps {
  employers: Employer[];
}

export default function Employers({ employers }: EmployersProps) {
  const topEmployers = employers.slice(0, 4);
  
  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('de-DE').format(num);
  };

  return (
    <div className="py-16 px-6 md:px-12 lg:px-20 bg-gray-50">
      <div className="container mx-auto max-w-6xl">
        <h2 className="text-4xl font-bold mb-2">Namhafte</h2>
        <h3 className="text-3xl font-bold mb-8 text-invenio-gold">ARBEITGEBER</h3>

        {/* Employer Cards */}
        <div className="grid md:grid-cols-2 gap-8 mb-12">
          {topEmployers.map((employer, index) => (
            <Card key={employer.id} className="hover:shadow-xl transition-shadow">
              <CardContent className="p-8">
                <div className="flex items-start justify-between mb-4">
                  <h4 className="text-2xl font-bold uppercase">{employer.name}</h4>
                  <div className="bg-invenio-gold/10 p-3 rounded-full">
                    <Building2 className="w-6 h-6 text-invenio-gold" />
                  </div>
                </div>
                
                <p className="text-gray-700 mb-6 leading-relaxed">
                  {employer.description}
                </p>
                
                <div className="flex items-center gap-2 text-invenio-gold">
                  <Users className="w-5 h-5" />
                  <span className="font-bold text-lg">
                    {formatNumber(employer.employees)} Mitarbeiter
                  </span>
                  <span className="text-gray-600">in der Region</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Map Section */}
        <Card className="bg-invenio-beige/20 border-0">
          <CardContent className="p-8">
            <h4 className="text-2xl font-bold mb-6 flex items-center gap-3">
              <MapPin className="w-6 h-6 text-invenio-gold" />
              Top 4 Arbeitgeber in Nürnberg
            </h4>
            
            {/* Placeholder for Map */}
            <div className="relative h-96 bg-gray-200 rounded-lg overflow-hidden">
              <img
                src="/images/nuremberg-employers-map.jpg"
                alt="Arbeitgeber Standorte"
                className="w-full h-full object-cover"
              />
              
              {/* Employer Markers */}
              <div className="absolute inset-0">
                {/* These would be positioned based on actual coordinates */}
                <div className="absolute top-1/4 left-1/3 bg-red-600 text-white px-3 py-1 rounded shadow-lg text-sm font-bold">
                  Stadt Nürnberg
                </div>
                <div className="absolute top-1/3 right-1/3 bg-blue-600 text-white px-3 py-1 rounded shadow-lg text-sm font-bold">
                  SIEMENS
                </div>
                <div className="absolute bottom-1/3 left-1/2 bg-green-600 text-white px-3 py-1 rounded shadow-lg text-sm font-bold">
                  MAN
                </div>
                <div className="absolute bottom-1/4 left-1/4 bg-purple-600 text-white px-3 py-1 rounded shadow-lg text-sm font-bold">
                  DATEV
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}