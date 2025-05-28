// app/admin/page.tsx
"use client";

import React, { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Plus, Edit, Trash, Upload, MapPin, Building, Image } from 'lucide-react';

export default function AdminInterface() {
  const [locations, setLocations] = useState<any[]>([]);
  const [employers, setEmployers] = useState<any[]>([]);
  const [selectedLocation, setSelectedLocation] = useState<string>('');
  const [isLocationDialogOpen, setIsLocationDialogOpen] = useState(false);
  const [isEmployerDialogOpen, setIsEmployerDialogOpen] = useState(false);
  const [isImageDialogOpen, setIsImageDialogOpen] = useState(false);

  // Form states
  const [locationForm, setLocationForm] = useState({
    city: '',
    inhabitants: '',
    populationGrowth: '',
    description: '',
    investmentHighlights: '',
  });

  const [employerForm, setEmployerForm] = useState({
    name: '',
    description: '',
    employees: '',
    locationId: '',
  });

  const handleLocationSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    // API call to save location
    console.log('Saving location:', locationForm);
    setIsLocationDialogOpen(false);
    // Reset form
    setLocationForm({
      city: '',
      inhabitants: '',
      populationGrowth: '',
      description: '',
      investmentHighlights: '',
    });
  };

  const handleEmployerSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    // API call to save employer
    console.log('Saving employer:', employerForm);
    setIsEmployerDialogOpen(false);
    // Reset form
    setEmployerForm({
      name: '',
      description: '',
      employees: '',
      locationId: '',
    });
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="container mx-auto max-w-7xl">
        <h1 className="text-3xl font-bold mb-8">Standort-Verwaltung</h1>

        <Tabs defaultValue="locations" className="space-y-4">
          <TabsList>
            <TabsTrigger value="locations" className="flex items-center gap-2">
              <MapPin className="w-4 h-4" />
              Standorte
            </TabsTrigger>
            <TabsTrigger value="employers" className="flex items-center gap-2">
              <Building className="w-4 h-4" />
              Arbeitgeber
            </TabsTrigger>
            <TabsTrigger value="images" className="flex items-center gap-2">
              <Image className="w-4 h-4" />
              Bilder
            </TabsTrigger>
          </TabsList>

          {/* Locations Tab */}
          <TabsContent value="locations">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Standorte verwalten</CardTitle>
                <Dialog open={isLocationDialogOpen} onOpenChange={setIsLocationDialogOpen}>
                  <DialogTrigger asChild>
                    <Button>
                      <Plus className="w-4 h-4 mr-2" />
                      Neuer Standort
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="max-w-2xl">
                    <DialogHeader>
                      <DialogTitle>Standort hinzufügen</DialogTitle>
                      <DialogDescription>
                        Fügen Sie einen neuen Standort mit allen relevanten Informationen hinzu.
                      </DialogDescription>
                    </DialogHeader>
                    <form onSubmit={handleLocationSubmit} className="space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <Label htmlFor="city">Stadt</Label>
                          <Input
                            id="city"
                            value={locationForm.city}
                            onChange={(e) => setLocationForm({ ...locationForm, city: e.target.value })}
                            required
                          />
                        </div>
                        <div>
                          <Label htmlFor="inhabitants">Einwohner</Label>
                          <Input
                            id="inhabitants"
                            type="number"
                            value={locationForm.inhabitants}
                            onChange={(e) => setLocationForm({ ...locationForm, inhabitants: e.target.value })}
                            required
                          />
                        </div>
                      </div>
                      <div>
                        <Label htmlFor="populationGrowth">Bevölkerungswachstum (%)</Label>
                        <Input
                          id="populationGrowth"
                          type="number"
                          step="0.1"
                          value={locationForm.populationGrowth}
                          onChange={(e) => setLocationForm({ ...locationForm, populationGrowth: e.target.value })}
                          required
                        />
                      </div>
                      <div>
                        <Label htmlFor="description">Beschreibung</Label>
                        <Textarea
                          id="description"
                          rows={4}
                          value={locationForm.description}
                          onChange={(e) => setLocationForm({ ...locationForm, description: e.target.value })}
                          required
                        />
                      </div>
                      <div>
                        <Label htmlFor="investmentHighlights">Investment Highlights (eines pro Zeile)</Label>
                        <Textarea
                          id="investmentHighlights"
                          rows={6}
                          value={locationForm.investmentHighlights}
                          onChange={(e) => setLocationForm({ ...locationForm, investmentHighlights: e.target.value })}
                          placeholder="Messe Nürnberg&#10;Automobilindustrie&#10;Medizintechnik&#10;..."
                          required
                        />
                      </div>
                      <div className="flex justify-end gap-2">
                        <Button type="button" variant="outline" onClick={() => setIsLocationDialogOpen(false)}>
                          Abbrechen
                        </Button>
                        <Button type="submit">Speichern</Button>
                      </div>
                    </form>
                  </DialogContent>
                </Dialog>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Stadt</TableHead>
                      <TableHead>Einwohner</TableHead>
                      <TableHead>Wachstum</TableHead>
                      <TableHead>Highlights</TableHead>
                      <TableHead className="text-right">Aktionen</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {locations.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center text-gray-500 py-8">
                          Keine Standorte vorhanden
                        </TableCell>
                      </TableRow>
                    ) : (
                      locations.map((location) => (
                        <TableRow key={location.id}>
                          <TableCell className="font-medium">{location.city}</TableCell>
                          <TableCell>{location.inhabitants.toLocaleString('de-DE')}</TableCell>
                          <TableCell>+{location.populationGrowth}%</TableCell>
                          <TableCell>{location.investmentHighlights.length} Highlights</TableCell>
                          <TableCell className="text-right">
                            <Button variant="ghost" size="sm">
                              <Edit className="w-4 h-4" />
                            </Button>
                            <Button variant="ghost" size="sm">
                              <Trash className="w-4 h-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Employers Tab */}
          <TabsContent value="employers">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Arbeitgeber verwalten</CardTitle>
                <div className="flex items-center gap-4">
                  <select
                    className="px-4 py-2 border rounded-md"
                    value={selectedLocation}
                    onChange={(e) => setSelectedLocation(e.target.value)}
                  >
                    <option value="">Standort wählen...</option>
                    {locations.map((loc) => (
                      <option key={loc.id} value={loc.id}>
                        {loc.city}
                      </option>
                    ))}
                  </select>
                  <Dialog open={isEmployerDialogOpen} onOpenChange={setIsEmployerDialogOpen}>
                    <DialogTrigger asChild>
                      <Button disabled={!selectedLocation}>
                        <Plus className="w-4 h-4 mr-2" />
                        Neuer Arbeitgeber
                      </Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Arbeitgeber hinzufügen</DialogTitle>
                        <DialogDescription>
                          Fügen Sie einen neuen Arbeitgeber für den ausgewählten Standort hinzu.
                        </DialogDescription>
                      </DialogHeader>
                      <form onSubmit={handleEmployerSubmit} className="space-y-4">
                        <div>
                          <Label htmlFor="employerName">Name</Label>
                          <Input
                            id="employerName"
                            value={employerForm.name}
                            onChange={(e) => setEmployerForm({ ...employerForm, name: e.target.value })}
                            required
                          />
                        </div>
                        <div>
                          <Label htmlFor="employees">Anzahl Mitarbeiter</Label>
                          <Input
                            id="employees"
                            type="number"
                            value={employerForm.employees}
                            onChange={(e) => setEmployerForm({ ...employerForm, employees: e.target.value })}
                            required
                          />
                        </div>
                        <div>
                          <Label htmlFor="employerDescription">Beschreibung</Label>
                          <Textarea
                            id="employerDescription"
                            rows={4}
                            value={employerForm.description}
                            onChange={(e) => setEmployerForm({ ...employerForm, description: e.target.value })}
                            required
                          />
                        </div>
                        <div className="flex justify-end gap-2">
                          <Button type="button" variant="outline" onClick={() => setIsEmployerDialogOpen(false)}>
                            Abbrechen
                          </Button>
                          <Button type="submit">Speichern</Button>
                        </div>
                      </form>
                    </DialogContent>
                  </Dialog>
                </div>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Mitarbeiter</TableHead>
                      <TableHead>Standort</TableHead>
                      <TableHead className="text-right">Aktionen</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {employers.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={4} className="text-center text-gray-500 py-8">
                          Keine Arbeitgeber vorhanden
                        </TableCell>
                      </TableRow>
                    ) : (
                      employers.map((employer) => (
                        <TableRow key={employer.id}>
                          <TableCell className="font-medium">{employer.name}</TableCell>
                          <TableCell>{employer.employees.toLocaleString('de-DE')}</TableCell>
                          <TableCell>{employer.location}</TableCell>
                          <TableCell className="text-right">
                            <Button variant="ghost" size="sm">
                              <Edit className="w-4 h-4" />
                            </Button>
                            <Button variant="ghost" size="sm">
                              <Trash className="w-4 h-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Images Tab */}
          <TabsContent value="images">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Bilder verwalten</CardTitle>
                <Button>
                  <Upload className="w-4 h-4 mr-2" />
                  Bilder hochladen
                </Button>
              </CardHeader>
              <CardContent>
                <div className="text-center text-gray-500 py-12">
                  <Image className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                  <p>Bilderverwaltung wird hier angezeigt</p>
                  <p className="text-sm mt-2">Drag & Drop oder Click zum Hochladen</p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}