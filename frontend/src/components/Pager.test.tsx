import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Pager } from "./Pager";

const noop = () => {};

describe("Pager", () => {
  it("hides controls and shows a count when total fits one page", () => {
    const { container } = render(
      <Pager total={3} limit={25} offset={0} onChange={noop} />,
    );
    expect(container.querySelectorAll("button")).toHaveLength(0);
    expect(container.textContent).toContain("3 entries");
  });

  it("renders nothing for an empty list", () => {
    const { container } = render(
      <Pager total={0} limit={25} offset={0} onChange={noop} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("shows the correct range and disables Prev on the first page", () => {
    render(<Pager total={50} limit={25} offset={0} onChange={noop} />);
    expect(screen.getByText("1–25 of 50")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Prev/ })).toHaveProperty(
      "disabled",
      true,
    );
    expect(screen.getByRole("button", { name: /Next/ })).toHaveProperty(
      "disabled",
      false,
    );
  });

  it("clamps the range and disables Next on the last page", () => {
    const onChange = vi.fn();
    render(<Pager total={50} limit={25} offset={25} onChange={onChange} />);
    expect(screen.getByText("26–50 of 50")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Next/ })).toHaveProperty(
      "disabled",
      true,
    );
  });
});
