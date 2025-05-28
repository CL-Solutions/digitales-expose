// components/expose/RiskDisclosure.tsx
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertTriangle, TrendingUp, Shield, Info } from 'lucide-react';

export default function RiskDisclosure() {
  const risks = [
    {
      title: 'Standort',
      description: 'Der Kauf einer Immobilie kann eine sehr rentable Investitionsentscheidung sein, wenn sich der Standort auf Dauer bewährt. Dafür sind insbesondere Lage, Verkehrsanbindung, örtliche und regionale Wirtschaftskraft sowie Zukunftspotentiale entscheidend.',
    },
    {
      title: 'Fertigstellung',
      description: 'Nach dem Bauträgervertrag wird ein fester Erwerbspreis und ein Fertigstellungstermin vereinbart. Das Risiko von Kostensteigerungen, Bauzeit sowie der Fertigstellung übernimmt der Bauträger.',
    },
    {
      title: 'Wertentwicklung',
      description: 'Eine Immobilie stellt eine langfristige Anlageform dar. Der Verkaufspreis bestimmen die zum Veräußerungszeitpunkt herrschenden Marktverhältnisse. Es besteht das Risiko, dass bei einem Verkauf zu einem ungünstigen Zeitpunkt Verluste entstehen.',
    },
    {
      title: 'Mieteinnahmen',
      description: 'Wie sich die Mieten zukünftig entwickeln, hängt von einer Reihe unterschiedlichster Faktoren ab und kann daher nicht garantiert werden. Über die Dauer des Investitionszeitraumes sind die Mietsteigerungen schwer abzuschätzen.',
    },
    {
      title: 'Mietgarantie',
      description: 'Die Werthaltigkeit einer Mietgarantie hängt stets von der Bonität des Mietgarantiegebers ab. Die tatsächlich erzielte Miete nach Ablauf der Garantiefrist wird vom Markt bestimmt.',
    },
    {
      title: 'Steuerliche Grundlagen',
      description: 'Zur Berechnung der individuellen steuerlichen Auswirkung wird vor einer Kaufentscheidung die Hinzuziehung eines Steuerberaters empfohlen. Auf das mögliche Risiko einer Steuergesetzesänderung wird hingewiesen.',
    },
  ];

  return (
    <div className="py-16 px-6 md:px-12 lg:px-20 bg-white">
      <div className="container mx-auto max-w-6xl">
        <h2 className="text-4xl font-bold mb-2">Chancen</h2>
        <h3 className="text-3xl font-bold mb-8">UND RISIKEN</h3>

        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Info className="w-5 h-5 text-blue-600" />
              Chancen und Risiken beim Erwerb von Immobilien zur Kapitalanlage
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-700 leading-relaxed">
              Jede Investition enthält Chancen und Risiken. Auch bei dem vorliegenden Angebot 
              besteht die Möglichkeit einer wirtschaftlichen Verschlechterung - sei es aus 
              rechtlichen, wirtschaftlichen oder steuerlichen Gründen. Nachstehend sollen für 
              einen Erwerber die Chancen, aber auch die Risiken einer möglichen Investition in 
              ein Immobilienangebot dargestellt werden, um die individuelle Anlageentscheidung 
              zu unterstützen.
            </p>
          </CardContent>
        </Card>

        <div className="grid md:grid-cols-2 gap-6 mb-12">
          {risks.map((risk, index) => (
            <Card key={index} className="hover:shadow-lg transition-shadow">
              <CardHeader className="pb-4">
                <CardTitle className="text-lg flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-orange-500" />
                  {risk.title}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-gray-600 text-sm leading-relaxed">
                  {risk.description}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Opportunities Section */}
        <Card className="bg-gradient-to-r from-green-50 to-emerald-50 border-green-200">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="w-6 h-6 text-green-600" />
              Ihre Chancen bei dieser Investition
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-start gap-3">
              <div className="w-2 h-2 bg-green-600 rounded-full mt-2 flex-shrink-0" />
              <p className="text-gray-700">
                <strong>Inflationsschutz:</strong> Immobilien bieten einen natürlichen Schutz gegen 
                Inflation, da sowohl Mieten als auch Immobilienwerte tendenziell mit der Inflation steigen.
              </p>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-2 h-2 bg-green-600 rounded-full mt-2 flex-shrink-0" />
              <p className="text-gray-700">
                <strong>Steuervorteile:</strong> Nutzen Sie Sonderabschreibungen und steuerliche 
                Förderungen für Ihre Investition.
              </p>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-2 h-2 bg-green-600 rounded-full mt-2 flex-shrink-0" />
              <p className="text-gray-700">
                <strong>Wertsteigerung:</strong> Profitieren Sie von der langfristigen Wertsteigerung 
                in einem wachsenden Immobilienmarkt.
              </p>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-2 h-2 bg-green-600 rounded-full mt-2 flex-shrink-0" />
              <p className="text-gray-700">
                <strong>Passives Einkommen:</strong> Generieren Sie regelmäßige Mieteinnahmen bei 
                minimalem Verwaltungsaufwand.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Disclaimer */}
        <Card className="mt-8 bg-gray-50 border-gray-300">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Shield className="w-5 h-5 text-gray-600" />
              Haftungsausschluss
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-gray-600 leading-relaxed">
              Alle Angaben, Berechnungen und Zahlenbeispiele dieser Unterlagen entsprechen dem 
              augenblicklichen Planungsstand. Änderungen der Bauausführung und der Material- bzw. 
              Baustoffauswahl bleiben, soweit sie erforderlich, gleichwertig und dem Erwerber 
              zumutbar sind, vorbehalten. Für unrichtige oder unvollständige Angaben oder für die 
              Verletzung eventuell bestehender Aufklärungs- oder Hinweispflichten haftet die 
              Invenio GmbH nur bei Vorsatz oder grober Fahrlässigkeit.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}