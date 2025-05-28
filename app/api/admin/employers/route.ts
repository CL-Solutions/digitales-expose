// app/api/admin/employers/route.ts
import { NextResponse } from 'next/server';
import { prisma } from '@/lib/db';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const locationId = searchParams.get('locationId');

  try {
    const employers = await prisma.employer.findMany({
      where: locationId ? { locationId } : undefined,
      include: {
        location: true,
      },
    });

    return NextResponse.json(employers);
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to fetch employers' },
      { status: 500 }
    );
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { name, description, employees, locationId } = body;

    const employer = await prisma.employer.create({
      data: {
        name,
        description,
        employees: parseInt(employees),
        locationId,
      },
    });

    return NextResponse.json(employer);
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to create employer' },
      { status: 500 }
    );
  }
}