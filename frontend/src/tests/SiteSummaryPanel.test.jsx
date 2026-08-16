import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import SiteSummaryPanel from "../components/dashboard/SiteSummaryPanel.jsx";

describe("SiteSummaryPanel", () => {
  it("renders multiple sites", () => {
    render(
      <SiteSummaryPanel
        siteSummary={[
          { site_id: "1", site_code: "SITE-HQ", site_name: "Headquarters Depot", robot_count: 8 },
          { site_id: "2", site_code: "SITE-WH", site_name: "Westside Warehouse", robot_count: 4 },
        ]}
      />
    );
    expect(screen.getByText("SITE-HQ")).toBeInTheDocument();
    expect(screen.getByText("Headquarters Depot")).toBeInTheDocument();
    expect(screen.getByText("SITE-WH")).toBeInTheDocument();
    expect(screen.getByText("Westside Warehouse")).toBeInTheDocument();
  });

  it("preserves supplied ordering", () => {
    render(
      <SiteSummaryPanel
        siteSummary={[
          { site_id: "1", site_code: "SITE-B", site_name: "Site B", robot_count: 2 },
          { site_id: "2", site_code: "SITE-A", site_name: "Site A", robot_count: 5 },
        ]}
      />
    );
    const rows = screen.getAllByRole("row").slice(1);
    expect(rows[0]).toHaveTextContent("SITE-B");
    expect(rows[1]).toHaveTextContent("SITE-A");
  });

  it("renders zero-robot sites", () => {
    render(
      <SiteSummaryPanel
        siteSummary={[
          { site_id: "1", site_code: "SITE-EMPTY", site_name: "Empty Site", robot_count: 0 },
        ]}
      />
    );
    const row = screen.getAllByRole("row")[1];
    expect(row).toHaveTextContent("0");
  });

  it("handles empty array", () => {
    render(<SiteSummaryPanel siteSummary={[]} />);
    expect(screen.getByText("No sites available.")).toBeInTheDocument();
  });
});
