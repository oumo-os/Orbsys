"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/auth";

export default function RootPage() {
  const router = useRouter();
  const { isAuthenticated, member } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated) {
      // Check if any org exists for first-run detection
      fetch((process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000") + "/health")
        .then(r => r.json())
        .then(d => {
          router.replace(d.org_count === 0 ? "/setup" : "/auth/login");
        })
        .catch(() => router.replace("/auth/login"));
      return;
    }
    // Authenticated — go to active org or personal dashboard
    router.replace(member?.org_id ? "/org/commons" : "/me");
  }, [isAuthenticated, member, router]);

  return (
    <div style={{
      minHeight:"100vh", background:"#050505",
      display:"flex", alignItems:"center", justifyContent:"center",
    }}>
      <div style={{
        width:24, height:24, borderRadius:"50%",
        border:"1px solid #2a2a2a", borderTopColor:"#c8a96e",
        animation:"spin 0.8s linear infinite",
      }}/>
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );
}
