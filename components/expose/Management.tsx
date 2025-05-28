// components/expose/Management.tsx
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Shield, Euro, FileCheck, Users, Home, Settings, TrendingUp, FileText } from 'lucide-react';

export default function Management() {
  const services = [
    { icon: Users, text: 'Neuvermietung bei Mieterwechsel inkl. Bonitätsprüfung' },
    { icon: FileText, text: 'Mietvertragserstellung nach aktueller Rechtsprechung' },
    { icon: Home, text: 'Protokollierte Wohnungsübergaben inkl. anschließender Mieterummeldung' },
    { icon: Euro, text: 'Jährliche Nebenkostenabrechnung' },
    { icon: Shield, text: 'Kautionsverwaltung- und Abrechnung bei Auszug' },
    { icon: Users, text: 'Mieterbetreuung und Kommunikation' },
    { icon: Settings, text: 'Koordination von Instandhaltungs- und Instandsetzungsmaßnahmen' },
    { icon: TrendingUp, text: 'Durchsetzen von Mieterhöhungsverlangen nach aktueller Rechtsprechung' },
    { icon: FileCheck, text: 'Regelmäßige Wirtschaftlichkeitsberechnung mit Renditeerhöhungspotential' },
    { icon: Euro, text: 'Finanzmanagement und Reporting' },
  ];

  const insuranceFeatures = [
    'Übernahme von Mietrückständen und entgangenen Mieteinnahmen',
    'Kostenerstattung bei durch Mieter verursachten Sachschäden',
    'Sofortiger Versicherungsschutz für Neu- und Bestandsmieter',
    'Schnelle Auszahlung im Schadensfall',
  ];

  return (
    <div className="py-16 px-6 md:px-12 lg:px-20 bg-gray-50">
      <div className="container mx-auto max-w-6xl">
        {/* Property Management */}
        <div className="mb-16">
          <h2 className="text-4xl font-bold mb-2">Verwaltung</h2>
          <h3 className="text-2xl mb-8 text-invenio-gold">VOR ORT</h3>

          <Card>
            <CardHeader>
              <CardTitle>Unser 360°-Servicepaket beinhaltet u. a. folgende Leistungen:</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-2 gap-4">
                {services.map((service, index) => {
                  const Icon = service.icon;
                  return (
                    <div key={index} className="flex items-start gap-3">
                      <Icon className="w-5 h-5 text-invenio-gold mt-0.5 flex-shrink-0" />
                      <span className="text-gray-700">{service.text}</span>
                    </div>
                  );
                })}
              </div>

              <div className="mt-8 p-6 bg-gray-100 rounded-lg">
                <p className="text-sm text-gray-600 mb-4">
                  Das Finanzmanagement beinhaltet die Abwicklung aller objektrelevanten Zahlungen über 
                  ein separates Mietkonto sowie die Entgegennahme und Überprüfung der monatlichen 
                  Mietzahlung. Hierfür wird für den Eigentümer ein eigenes Treuhandkonto eingerichtet. 
                  Der Eigentümer erhält nach Abzug aller monatlichen Kosten den Reinertrag auf dessen 
                  Konto überwiesen. Eine detaillierte Ein- und Ausgabeliste (Reporting) sorgt monatlich 
                  für Transparenz sowohl beim Eigentümer als auch ggf. bei dessen Steuerberater.
                </p>

                <div className="bg-invenio-gold text-white p-4 rounded-lg">
                  <h4 className="font-bold mb-2">ANGEBOT 360°+</h4>
                  <p className="text-lg">Mietverwaltungsservice inkl. Finanzmanagement</p>
                  <p className="text-2xl font-bold mt-2">
                    119,00 € monatlich pro Wohnung (WG-Konzept mit 4 Zimmern)
                  </p>
                  <p className="text-sm mt-1">Inkl. gesetzl. MwSt.</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Rental Insurance */}
        <div>
          <h2 className="text-4xl font-bold mb-2">Sicher</h2>
          <h3 className="text-3xl font-bold mb-8 text-invenio-gold">VERMIETEN</h3>

          <Card>
            <CardHeader>
              <CardTitle>Absicherung des Vermieters gegen Mietausfälle und Sachschäden</CardTitle>
              <p className="text-gray-600">
                Sicher Vermieten sichert Vermieter gegen finanzielle Einbußen bei privat vermieteten 
                Wohneinheiten ab. Ersetzt werden fehlende Mieteinnahmen sowie durch Mieter verursachte 
                Sachschäden und Renovierungskosten.
              </p>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-2 gap-6 mb-8">
                {insuranceFeatures.map((feature, index) => (
                  <div key={index} className="flex items-start gap-3">
                    <Shield className="w-5 h-5 text-green-600 mt-0.5 flex-shrink-0" />
                    <span className="text-gray-700">{feature}</span>
                  </div>
                ))}
              </div>

              {/* Insurance Packages */}
              <div className="grid md:grid-cols-3 gap-4">
                {[10000, 15000, 20000].map((amount) => (
                  <Card key={amount} className="text-center">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-lg">
                        Versicherte Schadenshöhe
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-3xl font-bold text-invenio-gold mb-2">
                        {amount.toLocaleString('de-DE')} €
                      </p>
                      <p className="text-lg font-semibold mb-4">
                        {amount === 10000 ? '269,10' : amount === 15000 ? '314,10' : '359,10'} €
                      </p>
                      <p className="text-sm text-gray-600">Prämie brutto p.a.</p>
                    </CardContent>
                  </Card>
                ))}
              </div>

              {/* Example Case */}
              <Card className="mt-8 bg-yellow-50 border-yellow-200">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <FileCheck className="w-5 h-5 text-yellow-600" />
                    Schadenbeispiel
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-700 mb-4">
                    Ein Mieter wird arbeitslos, bleibt über mehrere Monate die Miete schuldig und 
                    zieht dann überstürzt aus. Die Wohnung muss entrümpelt und renoviert werden. 
                    Zu den Miet- und Nebenkostenschulden kommen noch Kosten für Entrümpelung, 
                    Renovierung und entgangene Mieteinnahmen während der Renovierungszeit.
                  </p>
                  <div className="bg-white p-4 rounded">
                    <p className="font-semibold mb-2">Gesamtschaden: 14.000 EUR</p>
                    <p className="text-sm text-gray-600">
                      Bei einer Versicherungssumme von 15.000 EUR/Wohnung werden alle Kosten 
                      abzüglich Selbstbeteiligung (= Mietkaution) erstattet.
                    </p>
                  </div>
                </CardContent>
              </Card>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}