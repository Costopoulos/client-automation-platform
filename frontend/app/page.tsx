"use client";

import { Dashboard } from "@/components/Dashboard";
import { ScanButton } from "@/components/ScanButton";

export default function Home() {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">TechFlow Automation Platform</h1>
              <p className="text-sm text-muted-foreground">
                Intelligent data extraction and approval workflow
              </p>
            </div>
            <ScanButton />
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <Dashboard />
      </main>
    </div>
  );
}
