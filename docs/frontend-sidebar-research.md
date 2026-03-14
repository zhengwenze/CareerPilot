# Frontend Sidebar Research

## 1. Current project fit

- Current frontend stack: `Next.js 16 + React 19 + Tailwind CSS 4 + shadcn/ui`
- Current pages are still flat: `src/app/page.tsx`, `src/app/login/page.tsx`, `src/app/register/page.tsx`
- This means the best reference direction is not a generic admin template, but an `App Router + reusable layout shell + config-driven sidebar` architecture

## 2. Open-source references

### Reference A: shadcn/ui official sidebar

- Link: <https://ui.shadcn.com/docs/components/sidebar>
- Why it matters:
  - This is the most compatible baseline with our current component stack
  - It already defines the core composition model: `SidebarProvider`, `Sidebar`, `SidebarInset`, `SidebarTrigger`
- Worth learning:
  - Sidebar state is centrally managed instead of being scattered across pages
  - Supports collapsed icon mode, mobile drawer mode, and persistent open state
  - Encourages sidebar to be a reusable layout primitive, not page-local JSX

### Reference B: Kiranism/next-shadcn-dashboard-starter

- Repo: <https://github.com/Kiranism/next-shadcn-dashboard-starter>
- Key files:
  - `src/config/nav-config.ts`
  - `src/components/layout/app-sidebar.tsx`
  - `src/app/dashboard/layout.tsx`
- Worth learning:
  - Navigation data is extracted into `nav-config.ts`
  - `app-sidebar.tsx` focuses on rendering only
  - `dashboard/layout.tsx` is the real shell entry and wraps `SidebarProvider + Header + Sidebar + Content`
  - Menu config already leaves room for RBAC and org-aware visibility
- Takeaway:
  - `menu config` and `menu component` should be split
  - A route group layout should own the sidebar, not every page

### Reference C: rohitsoni007/shadcn-admin

- Repo: <https://github.com/rohitsoni007/shadcn-admin>
- Key files:
  - `src/components/layout/AppShell.tsx`
  - `src/components/layout/AppSidebar.tsx`
  - `src/lib/route-config.ts`
- Worth learning:
  - `AppShell` is responsible for the page frame: sidebar area, header area, main area, mobile behavior
  - `AppSidebar` handles collapsed and expanded rendering
  - Route permission rules are defined separately in `route-config.ts`
  - Accessibility is considered early, including skip links and semantic navigation landmarks
- Takeaway:
  - It is better to split `shell`, `sidebar`, and `route rules` into separate layers
  - Sidebar should be reusable, but routing and permission logic should not live inside raw JSX

### Reference D: dubinc/dub

- Repo: <https://github.com/dubinc/dub>
- Key files:
  - `apps/web/ui/layout/sidebar/app-sidebar-nav.tsx`
  - `apps/web/ui/layout/sidebar/sidebar-nav.tsx`
  - `apps/web/app/app.dub.co/(dashboard)/layout.tsx`
- Worth learning:
  - `sidebar-nav.tsx` is a generic navigation engine
  - `app-sidebar-nav.tsx` injects business data such as badge counts, active area, current workspace, and feature switches
  - Dashboard layout injects the sidebar into the main application frame instead of hard-coding it in pages
  - Navigation supports multi-area switching, grouped sections, badges, and dynamic item visibility
- Takeaway:
  - For medium-size products, the best pattern is often:
    - generic sidebar renderer
    - business navigation config
    - layout shell
  - Dynamic counts and conditional items should be computed outside the pure UI layer

## 3. Shared patterns across mature projects

After comparing the references above, the recurring structure is very stable:

1. `layout` owns the app shell
   - The sidebar is mounted once inside a route-group layout
   - Pages only render their own business content

2. navigation data is config-driven
   - Menu items are usually stored in `config/nav-config.ts` or a nearby navigation module
   - UI components map over config instead of hard-coding links inline

3. sidebar rendering is separated from business rules
   - The sidebar component handles appearance, collapsible state, nested menu rendering, and active styles
   - Business rules like roles, badges, workspace state, and feature flags live in hooks or config builders

4. route grouping is used to separate page families
   - Auth pages and dashboard pages usually have different layouts
   - This keeps login/register pages free from dashboard shell code

5. mobile and collapsed states are first-class
   - Mature projects consider mobile drawer behavior and icon-only collapse from the start
   - They do not treat the desktop sidebar as the only mode

## 4. Recommended structure for CareerPilot

Based on the current codebase and the references, the recommended next structure is:

```text
apps/web/src/
  app/
    (marketing)/
      page.tsx
    (auth)/
      login/page.tsx
      register/page.tsx
      layout.tsx
    (dashboard)/
      layout.tsx
      overview/page.tsx
      resume/page.tsx
      jobs/page.tsx
      applications/page.tsx
      interviews/page.tsx
      settings/page.tsx
  components/
    layout/
      app-shell.tsx
      app-sidebar.tsx
      app-header.tsx
      nav-main.tsx
      nav-user.tsx
    ui/
      sidebar.tsx
  config/
    nav-config.ts
  lib/
    route-access.ts
```

## 5. Suggested menu data model

The sidebar should be driven by structured data, for example:

```ts
export type NavItem = {
  title: string;
  href: string;
  icon?: string;
  match?: "exact" | "prefix";
  badge?: string | number;
  children?: NavItem[];
  roles?: string[];
  featureFlag?: string;
};
```

Recommended first-version main sections for CareerPilot:

- Overview
- Resume Center
- Job Matching
- Applications
- Mock Interviews
- Profile / Settings

## 6. Practical implementation decision

For this project, the most suitable approach is:

1. Use the `shadcn/ui sidebar` composition as the base primitive
2. Add a local `config/nav-config.ts` for all dashboard menu definitions
3. Create `src/app/(dashboard)/layout.tsx` as the only place that mounts the sidebar shell
4. Keep login and register under a separate `(auth)` route group
5. Leave room in the nav config for future role control and badge counts, even if v1 does not need them yet

## 7. Conclusion

The main lesson from mature open-source projects is simple:

- Do not write the left menu directly inside each page
- Do not mix menu data, permission logic, and visual rendering in one file
- Build one reusable `AppSidebar` component
- Mount it once in dashboard `layout.tsx`
- Drive it from a separate navigation config

This is the cleanest and most scalable direction for the current CareerPilot frontend.
