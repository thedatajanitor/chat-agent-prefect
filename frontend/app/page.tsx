'use client';

import { SimpleChat } from './simple-chat';

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24 bg-gray-50">
      <div className="w-full max-w-2xl">
        <h1 className="text-4xl font-bold text-center mb-8">
          Chat Agent with Prefect
        </h1>
        <div className="bg-white rounded-lg shadow-lg min-h-[600px] flex flex-col">
          <SimpleChat />
        </div>
      </div>
    </main>
  );
}