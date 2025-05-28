// components/expose/CoLivingFeatures.tsx
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Users, Shield, Clock, TrendingUp, Bed, Euro } from 'lucide-react';

export default function CoLivingFeatures() {
  const features = [
    {
      icon: Users,
      title: 'Sehr hohe Nachfrage nach WG-Wohnraum',
      description: 'Aufgrund der neuen Universität mit 6.000 Studenten in Nürnberg',
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
    },
    {
      icon: Bed,
      title: 'Ausstattung',
      description: 'Möblierung (Bett, Schrank, Schreibtisch, Stuhl, Spiegel, Lampe, Verdunkelung)',
      color: 'text-green-600',
      bgColor: 'bg-green-100',
    },
    {
      icon: Shield,
      title: 'Sicherheit',
      items: [
        'Mietausfallrisiko verteilt auf 4 Mieter',
        'Erstvermietungsgarantie in voller Höhe',
        'Gewährleistung der Modernisierung für 5 Jahre',
      ],
      color: 'text-purple-600',
      bgColor: 'bg-purple-100',
    },
    {
      icon: TrendingUp,
      title: 'Schutz vor Mietspiegel',
      items: [
        'Modernisierung auf Neubaustandard',
        'Einzelzimmervermietung',
        'Teilmöblierte Vermietung',
      ],
      color: 'text-orange-600',
      bgColor: 'bg-orange-100',
    },
    {
      icon: Clock,
      title: 'Geringer Zeitaufwand',
      description: 'Übergabe der Mieter in die Sondereigentumsverwaltung',
      color: 'text-indigo-600',
      bgColor: 'bg-indigo-100',
    },
  ];

  return (
    <div className="py-16 px-6 md:px-12 lg:px-20 bg-white">
      <div className="container mx-auto max-w-6xl">
        <h2 className="text-4xl font-bold mb-2">BESONDERHEITEN</h2>
        <h3 className="text-2xl mb-8 text-gray-600">CO-LIVING BEI INVENIO</h3>

        {/* News Article */}
        <Card className="mb-12 bg-gradient-to-r from-orange-50 to-red-50 border-orange-200">
          <CardContent className="p-8">
            <div className="flex items-start gap-6">
              <div className="flex-shrink-0">
                <div className="bg-orange-600 text-white px-4 py-2 rounded font-bold text-sm">
                  SPIEGEL Panorama
                </div>
              </div>
              <div>
                <h4 className="text-2xl font-bold mb-2">
                  Bayern spendiert Nürnberg eine neue Uni
                </h4>
                <p className="text-gray-700 mb-4">
                  Einmal Uni mit allem, bitte: Die bayerische Landesregierung hat eine komplett neue 
                  Universität geordert, für 1,2 Milliarden Euro. An der TU Nürnberg sollen künftig 
                  bis zu 6.000 Studenten büffeln.
                </p>
                <p className="text-sm text-gray-500">04.07.2018, 16:39 Uhr</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Features Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, index) => {
            const Icon = feature.icon;
            return (
              <Card key={index} className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className={`w-12 h-12 ${feature.bgColor} rounded-full flex items-center justify-center mb-4`}>
                    <Icon className={`w-6 h-6 ${feature.color}`} />
                  </div>
                  <CardTitle className="text-lg">{feature.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  {feature.description && (
                    <p className="text-gray-600">{feature.description}</p>
                  )}
                  {feature.items && (
                    <ul className="space-y-2">
                      {feature.items.map((item, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className={`${feature.color} mt-1`}>•</span>
                          <span className="text-gray-600 text-sm">{item}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Institutional Investment Reference */}
        <Card className="mt-12 bg-invenio-beige/20 border-invenio-gold">
          <CardContent className="p-8 text-center">
            <h4 className="text-xl font-semibold mb-4">
              Wir orientieren uns am Investmentgedanken der institutionellen Anleger
            </h4>
            <div className="flex justify-center items-center gap-8">
              <div className="text-2xl font-bold text-gray-700">Colonies</div>
              <div className="text-gray-400">und</div>
              <div className="text-2xl font-bold text-gray-700">Ares</div>
            </div>
            <p className="text-sm text-gray-600 mt-4">
              WG-Portfolio im Wert von einer Milliarde Dollar geplant
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}