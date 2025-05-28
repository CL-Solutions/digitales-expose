// lib/api-client.ts
export class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = '/api') {
    this.baseUrl = baseUrl;
  }

  async getProperty(id: string) {
    const response = await fetch(`${this.baseUrl}/properties/${id}`);
    if (!response.ok) throw new Error('Failed to fetch property');
    return response.json();
  }

  async getLocation(city: string) {
    const response = await fetch(`${this.baseUrl}/locations/${city}`);
    if (!response.ok) throw new Error('Failed to fetch location');
    return response.json();
  }

  async getLocations() {
    const response = await fetch(`${this.baseUrl}/admin/locations`);
    if (!response.ok) throw new Error('Failed to fetch locations');
    return response.json();
  }

  async createLocation(data: any) {
    const response = await fetch(`${this.baseUrl}/admin/locations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to create location');
    return response.json();
  }

  async getEmployers(locationId?: string) {
    const url = locationId
      ? `${this.baseUrl}/admin/employers?locationId=${locationId}`
      : `${this.baseUrl}/admin/employers`;
    const response = await fetch(url);
    if (!response.ok) throw new Error('Failed to fetch employers');
    return response.json();
  }

  async createEmployer(data: any) {
    const response = await fetch(`${this.baseUrl}/admin/employers`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to create employer');
    return response.json();
  }
}

export const apiClient = new ApiClient();