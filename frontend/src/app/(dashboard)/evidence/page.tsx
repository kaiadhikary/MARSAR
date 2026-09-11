"use client";

import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function EvidencePage() {
  return (
    <EmptyState
      title="NO CUSTODY HASH YET"
      description="Generate an STR from a transaction investigation to obtain a SHA-256 chain-of-custody digest."
      action={
        <Button asChild>
          <Link href="/reports">Open reports</Link>
        </Button>
      }
    />
  );
}
