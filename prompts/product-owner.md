You are an expert Product Owner for a traffic simulation system. Your job is to refine requirements and ask clarifying questions.

Read this initial idea:
- Traffic grid simulation
- Emergency vehicles get priority routing
- Traffic lights dynamically controlled
- 10x10 grid with roads, intersections, obstacles
- Vehicles move 1 cell per tick
- Traffic lights cycle automatically
- Emergency vehicles can trigger lights to turn green
- Real-time visualization via web interface

Ask me 5-10 critical questions that would help you define:
1. The MVP scope (what MUST be in v1?)
2. The data model (what entities exist?)
3. The user experience (who uses this and how?)
4. The success criteria (how do we know it works?)

Be specific. Don't just ask "what features?" —  for example ask "should emergency vehicles be able to reroute mid-journey if their path is blocked?"

After I answer, write a requirements document and save it to 
docs/requirements.md with this structure:

# Traffic Simulation System - Requirements

## Problem Statement
[What problem are we solving?]

## MVP Scope  
[What MUST be in version 1?]

## User Stories
[Who uses this and how?]

## Data Model
[What entities exist? What are their properties?]

## Edge Cases
[What unusual scenarios must we handle?]

## Success Criteria
[How do we know it works?]


critical clarifying questions:
Grid & Road Layout
Should the 10x10 grid be fully connected, or should some cells be non-traversable (buildings, parks, etc.)? If obstacles exist, are they static (placed at initialization) or can they appear dynamically (e.g., road construction, accidents)?
Are roads single-lane or multi-lane? Can vehicles pass each other on the same road segment, or does one vehicle block the cell entirely until it moves?
Vehicles & Movement
How many vehicle types exist in the MVP? Just "normal car" and "emergency vehicle," or do we also need buses, trucks, pedestrians, etc.?
How are vehicles spawned? Do they appear at random edges of the grid at a configurable rate, or does the user manually place them? Do vehicles have a destination (point A to B), or do they just flow through?
Should emergency vehicles be able to reroute mid-journey if their current path is blocked? Or do they follow a fixed pre-computed path and simply force traffic lights green along it?
Traffic Lights & Intersections
What is the light cycle model? Simple two-phase (green/red) or full four-phase (green/yellow/red/left-turn)? How long is each phase in ticks? Is the default cycle duration configurable?
When an emergency vehicle triggers a green light, what happens to cross-traffic? Does it immediately go red, or is there a yellow transition? How far in advance does the emergency vehicle "claim" an intersection?
User Experience
Who is the primary user — a student learning about traffic flow, a city planner evaluating scenarios, or a developer testing algorithms? This affects whether we need scenario presets, parameter tuning panels, or an API.
What controls does the user have at runtime? Can they pause/resume the simulation, adjust tick speed, manually place/remove obstacles, or spawn emergency vehicles on demand?
Success Criteria
How do we measure "emergency vehicle priority works"? Is there a target metric, like "emergency vehicles reach their destination in X% fewer ticks than normal vehicles," or is visual demonstration sufficient for the MVP?


Grid & Road Layout
1. Yes, some cells, must be non-traversable. For the initial version lets keep them static.
2. Let's keep it multi-lane

Vehicles & Movement
3. Let's just start with a normal car and an emergency vehicle for MVP
4. Vehicles appear at random edges of the grid at a configurable rate. Yes, vehicles have a destination(point A to B)
5. The whole idea is that emergency vehicles reach the destination fast, and the initial idea is to turn the signals green. But I like the idea to re-route in between and would like to take that in the next phase, for the initial phase, let it follow a fixed pre-computed path.

Traffic Lights & Intersections
6. Let's keep it a full four-phase. Each phase takes 3 ticks. Yes, the default cycle duration is configurable.
7. When an emergency vehicle triggers a green light, for the cross-traffic there is a yellow transition. The idea is that an emergency vehicle should have minimum or no wait at a signal, given that the cross traffic also needs to transition, let's say the emergency vehicle can claim an intersection from 4 units away.

User Experience
8. This idea is initiated by a developer, who wants to simulate the real-world traffic scenario via this. The final goal is running with an actual city map with live traffic and signal placements. But reaching there via multiple iterations and starting with really small and taking incremental steps, one little step at a time.
9. Yes user can pause or resume the simulation, adjust tick speed. Right now, we don't want users to manually place or remove obstacles or spawn emergency vehicles on demand. Keep it for the next phase.

Success Criteria
10. I would like to keep a target metric; the idea of "emergency vehicles reach their destination in X% fewer ticks than normal vehicles" sounds fine to me. We will keep the visual demonstration as well.

I hope this clears things out. If you are unsure about any of my answers or need more clarification, please ask before drafting the requirements document.


Thanks for the detailed answers. A couple of quick follow-ups before I draft the document:
Multi-lane clarification: On a 10x10 grid, how should we think about "multi-lane"? Does this mean each road cell can hold multiple vehicles simultaneously (e.g., 2 vehicles side-by-side in a cell, one per lane), allowing faster vehicles or emergency vehicles to pass slower ones? Or are you envisioning the grid cells themselves being subdivided into lanes?
Pathfinding algorithm preference: Since vehicles go from point A to B, should we use a standard shortest-path algorithm (like A) for route computation? And for emergency vehicles on their fixed path, is "shortest path" also the strategy, or should it be "fastest path" factoring in current light states?
Tick speed range: When the user adjusts tick speed, do you have a rough range in mind (e.g., 1 tick/second up to 10 ticks/second)? This helps define the real-time visualization requirements.
These are the only ambiguities I see. Everything else is clear enough to write a solid requirements doc.


1.Multi-lane clarification: I got this I guess with initial grid layout it will be diffcult and cumbersome to implement multi-lane, how about keeping it single-lane for the initial version. Later when we move to graphs we can have multi-lane
2. Pathfinding algorithm preference: yes we use a standard shortest-path algorithm for vehicles going from point A to B. For emergency vehicles it should it be "fastest path" factoring in current light states?
3. Tick speed range:- 1 tick/second up to 10 ticks/second sounds good.

Still if you havemore clarification or more questions, please clarify or ask before drafting requirements.