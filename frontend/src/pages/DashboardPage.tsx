import { UserCard } from "@/features/users/components/UserCard";

export function DashboardPage() {
  return (
    <section>
      <h2 className="text-2xl font-semibold text-slate-900">Dashboard</h2>
      <p className="mt-2 text-sm text-slate-600">
        Proof-of-concept data flow: React Query hook → Axios → FastAPI.
      </p>
      <div className="mt-6">
        <UserCard userId="1" />
      </div>
    </section>
  );
}
