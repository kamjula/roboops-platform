import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect } from "vitest";
import App from "../App.jsx";

describe("App", () => {
  it("renders shell", async () => {
    render(<MemoryRouter><App /></MemoryRouter>);
    expect(screen.getByText("RoboOps")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
  });
});
