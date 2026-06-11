import { useUser } from "@/features/users/api/getUser";

interface UserCardProps {
  userId: string;
}

export function UserCard({ userId }: UserCardProps) {
  const { data: user, isLoading, isError, error } = useUser(userId);

  if (isLoading) {
    return (
      <div className="animate-pulse rounded-lg border border-slate-200 p-6">
        <div className="h-4 w-1/3 rounded bg-slate-200" />
        <div className="mt-3 h-3 w-1/2 rounded bg-slate-100" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700">
        Failed to load user: {error.message}
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <article className="rounded-lg border border-slate-200 p-6 shadow-sm">
      <h3 className="text-lg font-medium text-slate-900">{user.full_name}</h3>
      <p className="mt-1 text-sm text-slate-600">{user.email}</p>
      <p className="mt-3 text-xs text-slate-500">
        Status: {user.is_active ? "Active" : "Inactive"} · ID: {user.id}
      </p>
    </article>
  );
}
