import { NavLink, useParams } from "react-router-dom";

const tabs = [
  { label: "Overview", path: "" },
  { label: "Saved Sources", path: "saved" },
  { label: "Mind Map", path: "mind-map" },
];

export function ProjectTabBar() {
  const { projectId } = useParams<{ projectId: string }>();

  return (
    <div className="border-b border-gray-200">
      <nav className="flex gap-6">
        {tabs.map((tab) => (
          <NavLink
            key={tab.path}
            to={`/projects/${projectId}${tab.path ? `/${tab.path}` : ""}`}
            end={tab.path === ""}
            className={({ isActive }) =>
              `border-b-2 pb-3 text-sm font-medium transition-colors ${
                isActive
                  ? "border-brand-700 text-brand-700"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
