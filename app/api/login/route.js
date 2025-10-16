import { NextResponse } from 'next/server';

export async function POST(request) {
  const { email, password } = await request.json();
  // Mock auth
  if (email === 'test@example.com' && password === 'pass') {
    return NextResponse.json({ message: 'Logged in' });
  }
  return NextResponse.json({ message: 'Failed' }, { status: 401 });
}