# Atlas Dark Interface Design System

## Product context

Atlas is a transparent local travel-planning application powered by Python LangGraph. Users describe a trip, refine structured requirements, receive a mock itinerary, review the cost and approve or request changes. Sherlock mode exposes the execution timeline, routing decisions, retries and checkpoints.

Primary jobs:
- Enter and edit travel requirements quickly.
- Understand the recommended flight, stay, activities and total cost.
- Approve or revise a plan with confidence.
- Learn how LangGraph executed the workflow without seeing private reasoning.

## Visual direction

Use a refined neural-noir dark interface, adapted for an operational application rather than a marketing landing page.

- Background: `#080A0C`.
- Raised surface: `#111417`.
- Secondary surface: `#171B1F`.
- Hairline border: `rgba(255,255,255,.09)`.
- Primary text: `#F3F1EA`.
- Secondary text: `#9A9DA2`.
- Accent: muted bronze `#B69A7D`.
- Success: `#85D89A`.
- Warning: `#E2B86B`.
- Error: `#EC7D76`.
- Do not use blue or purple gradients.
- Avoid decorative glassmorphism, random floating elements and excessive cards.

## Typography

- Use Inter or the operating-system sans stack for the entire product UI.
- Do not use a decorative serif: this is a planning tool, not an editorial site.
- Display: 56px desktop / 38px mobile, weight 650, tight tracking.
- Section heading: 24-30px, weight 620.
- Card title: 16-18px, weight 600.
- Body: 14-16px, line-height 1.55.
- Metadata: 11-12px uppercase, tracking `.10em`.

## Layout

- Desktop uses a 320px dark control rail and a fluid planning workspace.
- Keep the main content width around 1120px.
- Hero copy is compact; the itinerary is the dominant content after generation.
- Use an 8px spacing system and generous 24-32px section gaps.
- Mobile collapses into one column with requirements above results.

## Components

- Inputs use `#111417`, a subtle border and 12px radius; focused inputs receive a bronze border and soft ring.
- Primary button uses warm off-white text on bronze; secondary button uses transparent surface with a hairline border.
- Status chips are compact, semantic and never decorative.
- Summary metrics form one connected horizontal strip rather than four detached cards.
- Flight and stay use two calm detail panels with strong labels and clear secondary metadata.
- Activities display as simple list rows or pills, not separate cards.
- Approval panel is visually prominent but does not resemble a checkout.
- Sherlock timeline uses a vertical rail, node dots, timestamps, status chips and expandable technical details.

## Motion

- 160-220ms ease-out transitions.
- No parallax, pulsing backgrounds or ambient animation.
- Use motion only for expanding details, switching modes and showing newly completed nodes.

## Content and boundaries

- Clearly label all pricing as mock data.
- Preserve the three-attempt indicator and budget ceiling.
- Keep Sherlock mode accessible from a persistent switch.
- The interface must state that no booking or payment occurred.
- Never expose private chain-of-thought; show structured operational logs only.

