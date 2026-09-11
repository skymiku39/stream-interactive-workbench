/*
 * StreamSuite throw physics adapter.
 *
 * The renderer deliberately talks to this small compatibility layer instead of
 * embedding a second home-grown rigid-body solver in game_overlays.py.  The
 * implementation uses the vendored cannon-es build (MIT) and keeps CSS and
 * Three.js rendering on the same body/quaternion source of truth.
 */
(function installStreamThrowPhysics(global) {
  "use strict";

  const CANNON = global.CANNON;
  if (!CANNON) throw new Error("cannon-es must be loaded before throw_physics.js");

  const DEG2RAD = Math.PI / 180;
  const FACE_NORMALS = Object.freeze({
    1: Object.freeze({ x: 0, y: 0, z: 1 }),
    2: Object.freeze({ x: 1, y: 0, z: 0 }),
    3: Object.freeze({ x: 0, y: 0, z: -1 }),
    4: Object.freeze({ x: -1, y: 0, z: 0 }),
    5: Object.freeze({ x: 0, y: -1, z: 0 }),
    6: Object.freeze({ x: 0, y: 1, z: 0 })
  });

  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

  function hashSeed(value) {
    const text = String(value == null ? "" : value);
    let hash = 2166136261;
    for (let index = 0; index < text.length; index += 1) {
      hash ^= text.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }
    return hash >>> 0 || 0x6d2b79f5;
  }

  function seededRandom(seed) {
    let state = seed >>> 0 || 0x6d2b79f5;
    return function random() {
      state += 0x6d2b79f5;
      let value = state;
      value = Math.imul(value ^ (value >>> 15), value | 1);
      value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
      return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
    };
  }

  function vector(value) {
    return new CANNON.Vec3(Number(value.x) || 0, Number(value.y) || 0, Number(value.z) || 0);
  }

  function plainQuaternion(quaternion) {
    return { x: quaternion.x, y: quaternion.y, z: quaternion.z, w: quaternion.w };
  }

  function plainVector(value) {
    return { x: value.x, y: value.y, z: value.z };
  }

  function diceRotateVector(quaternion, value) {
    const q = new CANNON.Quaternion(quaternion.x, quaternion.y, quaternion.z, quaternion.w);
    const result = q.vmult(vector(value));
    return plainVector(result);
  }

  function diceDot(a, b) {
    return a.x * b.x + a.y * b.y + a.z * b.z;
  }

  function diceLocalNormalForFace(value) {
    return FACE_NORMALS[Number(value)] || null;
  }

  function diceFaceUpFromQuaternion(quaternion) {
    let best = { value: 1, alignment: -Infinity, normal: FACE_NORMALS[1] };
    for (const [rawValue, localNormal] of Object.entries(FACE_NORMALS)) {
      const normal = diceRotateVector(quaternion, localNormal);
      if (normal.y > best.alignment) {
        best = { value: Number(rawValue), alignment: normal.y, normal };
      }
    }
    return best;
  }

  function coinFaceUpFromQuaternion(quaternion) {
    const headsNormal = diceRotateVector(quaternion, { x: 0, y: 0, z: 1 });
    const alignment = Math.abs(headsNormal.y);
    if (alignment < 0.18) return { value: "?", alignment, edge: true, normal: headsNormal };
    return headsNormal.y >= 0
      ? { value: "正面", alignment: headsNormal.y, normal: headsNormal }
      : { value: "反面", alignment: -headsNormal.y, normal: headsNormal };
  }

  function diceQuatToCssMatrix3d(quaternion) {
    const q = new CANNON.Quaternion(quaternion.x, quaternion.y, quaternion.z, quaternion.w);
    q.normalize();
    const x = q.x;
    const y = q.y;
    const z = q.z;
    const w = q.w;
    const xx = x * x;
    const yy = y * y;
    const zz = z * z;
    const xy = x * y;
    const xz = x * z;
    const yz = y * z;
    const wx = w * x;
    const wy = w * y;
    const wz = w * z;
    const values = [
      1 - 2 * (yy + zz), 2 * (xy + wz), 2 * (xz - wy), 0,
      2 * (xy - wz), 1 - 2 * (xx + zz), 2 * (yz + wx), 0,
      2 * (xz + wy), 2 * (yz - wx), 1 - 2 * (xx + yy), 0,
      0, 0, 0, 1
    ];
    return `matrix3d(${values.map(value => Math.abs(value) < 1e-10 ? 0 : value).join(",")})`;
  }

  function diceFloorContact(body) {
    const q = body.q;
    let supportHeight = body.radius;
    if (body.shape === "box") {
      const axisX = diceRotateVector(q, { x: 1, y: 0, z: 0 });
      const axisY = diceRotateVector(q, { x: 0, y: 1, z: 0 });
      const axisZ = diceRotateVector(q, { x: 0, y: 0, z: 1 });
      supportHeight = body.halfExtent * (Math.abs(axisX.y) + Math.abs(axisY.y) + Math.abs(axisZ.y));
    } else if (body.shape === "coin") {
      const faceAxis = diceRotateVector(q, { x: 0, y: 0, z: 1 });
      const axial = Math.abs(faceAxis.y);
      supportHeight = body.halfThickness * axial + body.radius * Math.sqrt(Math.max(0, 1 - axial * axial));
    }
    return {
      minY: body.y - supportHeight,
      point: { x: body.x, y: body.y - supportHeight, z: body.z }
    };
  }

  class RigidBody3D {
    constructor(options) {
      const opts = options || {};
      this.options = { ...opts };
      this.element = opts.element || null;
      this.shadowElement = opts.shadowElement || null;
      this.threeMesh = opts.threeMesh || null;
      this.shape = opts.shape || "sphere";
      this.radius = Number(opts.radius) || 34;
      this.halfThickness = Number(opts.halfThickness) || 7;
      this.halfExtent = Number(opts.halfExtent) || this.radius;
      this.mass = Number(opts.mass) || 1;
      this.restitution = opts.restitution == null ? 0.45 : Number(opts.restitution);
      this.friction = opts.friction == null ? 0.55 : Number(opts.friction);
      this.surfaceFriction = opts.surfaceFriction == null ? this.friction : Number(opts.surfaceFriction);
      this.airDrag = opts.airDrag == null ? 0.995 : Number(opts.airDrag);
      this.rotDamping = opts.rotDamping == null ? 0.985 : Number(opts.rotDamping);
      this.shadowOpacity = opts.shadowOpacity == null ? 0.75 : Number(opts.shadowOpacity);
      this.targetFace = Number.isInteger(Number(opts.targetFace)) ? Number(opts.targetFace) : null;
      this.targetCoinSide = opts.targetCoinSide === "正面" || opts.targetCoinSide === "反面"
        ? opts.targetCoinSide
        : null;
      this.onBounce = typeof opts.onBounce === "function" ? opts.onBounce : null;
      this.onWallHit = typeof opts.onWallHit === "function" ? opts.onWallHit : null;
      this.onSettle = null;
      this.finalFace = null;
      this.restTime = 0;
      this.faceStableTime = 0;
      this.settledFaceStableTime = 0;
      this.lastObservedFace = null;
      this.angularTravel = 0;
      this.unstableContactTime = 0;
      this.supportContact = null;
      this.lastBounceAt = 0;
      this.cannonBody = null;
      this.initialState = {
        x: Number(opts.x) || 0,
        y: opts.y == null ? 200 : Number(opts.y),
        z: Number(opts.z) || 0,
        vx: Number(opts.vx) || 0,
        vy: Number(opts.vy) || 0,
        vz: Number(opts.vz) || 0,
        rx: Number(opts.rx) || 0,
        ry: Number(opts.ry) || 0,
        rz: Number(opts.rz) || 0,
        wx: Number(opts.wx) || 0,
        wy: Number(opts.wy) || 0,
        wz: Number(opts.wz) || 0
      };
    }

    get x() { return this.cannonBody ? this.cannonBody.position.x : this.initialState.x; }
    get y() { return this.cannonBody ? this.cannonBody.position.y : this.initialState.y; }
    get z() { return this.cannonBody ? this.cannonBody.position.z : this.initialState.z; }
    get vx() { return this.cannonBody ? this.cannonBody.velocity.x : this.initialState.vx; }
    get vy() { return this.cannonBody ? this.cannonBody.velocity.y : this.initialState.vy; }
    get vz() { return this.cannonBody ? this.cannonBody.velocity.z : this.initialState.vz; }
    get q() {
      if (this.cannonBody) return plainQuaternion(this.cannonBody.quaternion);
      const q = new CANNON.Quaternion();
      q.setFromEuler(this.initialState.rx * DEG2RAD, this.initialState.ry * DEG2RAD, this.initialState.rz * DEG2RAD, "XYZ");
      return plainQuaternion(q);
    }
    get angularVelocity() {
      if (this.cannonBody) return plainVector(this.cannonBody.angularVelocity);
      return {
        x: this.initialState.wx * DEG2RAD,
        y: this.initialState.wy * DEG2RAD,
        z: this.initialState.wz * DEG2RAD
      };
    }
    get settled() {
      return Boolean(this.cannonBody && this.cannonBody.sleepState === CANNON.Body.SLEEPING);
    }
  }

  class StreamPhysicsWorld {
    constructor(arenaElement, webglEngine, tuning) {
      this.arena = arenaElement || null;
      this.webglEngine = webglEngine || null;
      this.tuning = tuning || {};
      this.planeY = 0;
      this.gravity = -Math.abs(Number(this.tuning.gravity) || 1200);
      this.bounds = { minX: -200, maxX: 200, minZ: -100, maxZ: 100 };
      this.bodies = [];
      this.world = null;
      this.isRunning = false;
      this.rafId = null;
      this.lastTime = 0;
      this.fixedDt = 1 / 120;
      this.maxSubSteps = 8;
      this.onSettled = null;
      this.resultPolicy = String(this.tuning.resultPolicy || "event-replay");
      this.physicsSeed = hashSeed(this.tuning.physicsSeed || `${Date.now()}-${Math.random()}`);
      this.replaySeed = null;
      this.replayBias = false;
      this._prepared = false;
      this._settledReported = false;
      this.engineName = "cannon-es";
    }

    addBody(body) {
      this.bodies.push(body);
      this._prepared = false;
    }

    stop() {
      this.isRunning = false;
      if (this.rafId != null) cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }

    _shapeFor(body) {
      if (body.shape === "box") return { shape: new CANNON.Box(new CANNON.Vec3(body.halfExtent, body.halfExtent, body.halfExtent)) };
      if (body.shape === "coin") {
        // More edge segments make the final coin wobble roll continuously
        // instead of visibly stepping from one coarse cylinder facet to the
        // next immediately before sleeping.
        const shape = new CANNON.Cylinder(body.radius, body.radius, body.halfThickness * 2, 64);
        const orientation = new CANNON.Quaternion();
        orientation.setFromEuler(Math.PI / 2, 0, 0, "XYZ");
        return { shape, orientation };
      }
      return { shape: new CANNON.Sphere(body.radius) };
    }

    _createWorld() {
      const world = new CANNON.World({ gravity: new CANNON.Vec3(0, this.gravity, 0), allowSleep: true });
      // Reference Dice/DiceRisky builds use NaiveBroadphase.  With at most a
      // handful of throw bodies its O(n²) cost is negligible, and stable pair
      // ordering makes seeded multi-body replay deterministic.
      world.broadphase = new CANNON.NaiveBroadphase();
      world.solver.iterations = 20;
      world.solver.tolerance = 1e-5;
      world.defaultContactMaterial.contactEquationStiffness = 1e7;
      world.defaultContactMaterial.contactEquationRelaxation = 4;

      const floorMaterial = new CANNON.Material("throw-floor");
      const floor = new CANNON.Body({ mass: 0, material: floorMaterial });
      floor.addShape(new CANNON.Plane());
      floor.quaternion.setFromEuler(-Math.PI / 2, 0, 0, "XYZ");
      floor.position.y = this.planeY;
      floor.userData = { kind: "floor" };
      world.addBody(floor);

      // Cannon has no CCD for these bodies. A thin decorative wall can be
      // crossed in one high-speed fixed step, so use deep invisible colliders
      // whose inner face still lands exactly on the configured bounds.
      const thickness = 48;
      // Dice enter above y=300 in some presets.  Walls must extend above every
      // spawn arc; otherwise a body can be physically valid yet settle beyond
      // the visible tabletop.
      const wallHeight = 800;
      const width = this.bounds.maxX - this.bounds.minX;
      const depth = this.bounds.maxZ - this.bounds.minZ;
      const walls = [
        { position: [this.bounds.minX - thickness, wallHeight / 2, 0], half: [thickness, wallHeight / 2, depth / 2 + thickness], kind: "wall" },
        { position: [this.bounds.maxX + thickness, wallHeight / 2, 0], half: [thickness, wallHeight / 2, depth / 2 + thickness], kind: "wall" },
        { position: [0, wallHeight / 2, this.bounds.minZ - thickness], half: [width / 2 + thickness, wallHeight / 2, thickness], kind: "wall" },
        { position: [0, wallHeight / 2, this.bounds.maxZ + thickness], half: [width / 2 + thickness, wallHeight / 2, thickness], kind: "wall" }
      ];
      for (const wallSpec of walls) {
        const wall = new CANNON.Body({ mass: 0, material: floorMaterial });
        wall.addShape(new CANNON.Box(new CANNON.Vec3(...wallSpec.half)));
        wall.position.set(...wallSpec.position);
        wall.userData = { kind: wallSpec.kind };
        world.addBody(wall);
      }
      return { world, floorMaterial };
    }

    _targetNormal(body) {
      if (body.shape === "box" && body.targetFace) return diceLocalNormalForFace(body.targetFace);
      if (body.shape === "coin" && body.targetCoinSide) {
        return { x: 0, y: 0, z: body.targetCoinSide === "正面" ? 1 : -1 };
      }
      return null;
    }

    _candidateState(body, seed, index, targetBias) {
      const random = seededRandom(hashSeed(`${seed}:${index}`));
      const base = body.initialState;
      const state = {
        position: new CANNON.Vec3(
          base.x + (random() - 0.5) * 10,
          base.y + random() * 14,
          base.z + (random() - 0.5) * 10
        ),
        velocity: new CANNON.Vec3(
          base.vx * (0.88 + random() * 0.24) + (random() - 0.5) * 24,
          base.vy * (0.90 + random() * 0.20),
          base.vz * (0.88 + random() * 0.24) + (random() - 0.5) * 24
        ),
        quaternion: new CANNON.Quaternion(),
        angularVelocity: new CANNON.Vec3(
          base.wx * DEG2RAD,
          base.wy * DEG2RAD,
          base.wz * DEG2RAD
        )
      };

      const targetNormal = targetBias ? this._targetNormal(body) : null;
      if (targetNormal) {
        const align = new CANNON.Quaternion();
        align.setFromVectors(vector(targetNormal), new CANNON.Vec3(0, 1, 0));
        const yaw = new CANNON.Quaternion();
        yaw.setFromAxisAngle(new CANNON.Vec3(0, 1, 0), random() * Math.PI * 2);
        const tiltAxis = new CANNON.Vec3(random() - 0.5, 0, random() - 0.5);
        if (tiltAxis.lengthSquared() < 1e-6) tiltAxis.set(1, 0, 0);
        tiltAxis.normalize();
        const tilt = new CANNON.Quaternion();
        const conservative = targetBias === "conservative";
        const stableReplay = targetBias === "stable";
        const ordinaryTilt = body.shape === "coin" ? 1.90 : 1.42;
        tilt.setFromAxisAngle(
          tiltAxis,
          stableReplay ? (random() - 0.5) * 0.10 : (random() - 0.5) * (conservative ? 0.32 : ordinaryTilt)
        );
        yaw.mult(tilt, state.quaternion);
        state.quaternion.mult(align, state.quaternion);
        const signed = (minimum, spread) => (random() < 0.5 ? -1 : 1) * (minimum + random() * spread);
        if (stableReplay) {
          state.angularVelocity.set(0, signed(40, 12), 0);
        } else if (conservative) {
          state.angularVelocity.set(
            signed(body.shape === "coin" ? 3.5 : 2.0, 3.0),
            signed(18, 10),
            signed(body.shape === "coin" ? 2.5 : 2.0, 3.0)
          );
        } else if (body.shape === "coin") {
          // A coin needs substantial transverse spin to visibly flip. Axial
          // spin alone only rotates its artwork while it stays face-up.
          state.angularVelocity.set(signed(16, 14), signed(13, 13), signed(5, 10));
        } else {
          // Give dice a genuinely three-axis tumble instead of a mostly-yaw
          // replay. Candidate simulation still decides whether it lands on
          // the event face; the visible throw receives no later correction.
          state.angularVelocity.set(signed(11, 13), signed(12, 14), signed(10, 14));
        }
        if (stableReplay) {
          state.position.y = Math.max(body.radius + 72, Math.min(base.y, 140));
          state.velocity.set(0, -72, 0);
        }
      } else {
        state.quaternion.setFromEuler(
          (base.rx + random() * 36 - 18) * DEG2RAD,
          (base.ry + random() * 36 - 18) * DEG2RAD,
          (base.rz + random() * 36 - 18) * DEG2RAD,
          "XYZ"
        );
      }
      return state;
    }

    _createCannonBody(wrapper, state, material, planning) {
      const body = new CANNON.Body({
        mass: wrapper.mass,
        material,
        position: state.position.clone(),
        quaternion: state.quaternion.clone(),
        velocity: state.velocity.clone(),
        angularVelocity: state.angularVelocity.clone(),
        linearDamping: clamp(1 - wrapper.airDrag, 0.01, 0.16),
        angularDamping: clamp(1 - wrapper.rotDamping, 0.02, 0.32),
        allowSleep: true,
        sleepSpeedLimit: wrapper.shape === "coin" ? 1.1 : 3.2,
        sleepTimeLimit: wrapper.shape === "coin" ? 0.82 : 0.38
      });
      const shapeSpec = this._shapeFor(wrapper);
      body.addShape(shapeSpec.shape, undefined, shapeSpec.orientation);
      body.userData = { wrapper, planning: Boolean(planning) };
      return body;
    }

    _populateWorld(seed, planning, targetBias) {
      const setup = this._createWorld();
      const dynamicBodies = [];
      const materials = [];
      this.bodies.forEach((wrapper, index) => {
        const material = new CANNON.Material(`throw-body-${index}`);
        materials.push(material);
        setup.world.addContactMaterial(new CANNON.ContactMaterial(setup.floorMaterial, material, {
          friction: clamp(wrapper.surfaceFriction, 0, 1),
          restitution: clamp(wrapper.restitution, 0, 1),
          contactEquationStiffness: 1e7,
          contactEquationRelaxation: 4
        }));
        const state = this._candidateState(wrapper, seed, index, targetBias);
        const cannonBody = this._createCannonBody(wrapper, state, material, planning);
        setup.world.addBody(cannonBody);
        dynamicBodies.push(cannonBody);
      });
      for (let first = 0; first < materials.length; first += 1) {
        for (let second = first; second < materials.length; second += 1) {
          const a = this.bodies[first];
          const b = this.bodies[second];
          setup.world.addContactMaterial(new CANNON.ContactMaterial(materials[first], materials[second], {
            friction: clamp(Math.min(a.friction, b.friction), 0, 1),
            restitution: clamp(Math.min(a.restitution, b.restitution), 0, 1)
          }));
        }
      }
      return { ...setup, dynamicBodies };
    }

    _resultFor(wrapper, cannonBody) {
      const quaternion = plainQuaternion(cannonBody.quaternion);
      return wrapper.shape === "coin"
        ? coinFaceUpFromQuaternion(quaternion).value
        : diceFaceUpFromQuaternion(quaternion).value;
    }

    _seedMatches(seed, targetBias) {
      const simulation = this._populateWorld(seed, true, targetBias);
      const maxSteps = Math.ceil(7.5 / this.fixedDt);
      const targetStableSteps = simulation.dynamicBodies.map(() => 0);
      for (let step = 0; step < maxSteps; step += 1) {
        simulation.world.step(this.fixedDt);
        simulation.dynamicBodies.forEach((body, index) => {
          const wrapper = this.bodies[index];
          const target = wrapper.targetFace || wrapper.targetCoinSide;
          if (!target || this._resultFor(wrapper, body) === target) targetStableSteps[index] += 1;
          else targetStableSteps[index] = 0;
        });
        if (simulation.dynamicBodies.every(body => body.sleepState === CANNON.Body.SLEEPING)) break;
      }
      if (!simulation.dynamicBodies.every(body => body.sleepState === CANNON.Body.SLEEPING)) return false;
      return simulation.dynamicBodies.every((body, index) => {
        const wrapper = this.bodies[index];
        const target = wrapper.targetFace || wrapper.targetCoinSide;
        const stableEnough = wrapper.shape !== "coin" || targetStableSteps[index] >= Math.ceil(0.62 / this.fixedDt);
        return !target || (this._resultFor(wrapper, body) === target && stableEnough);
      });
    }

    _selectReplaySeed() {
      const hasTargets = this.bodies.some(body => body.targetFace || body.targetCoinSide);
      if (!hasTargets || this.resultPolicy === "natural") {
        return { seed: this.physicsSeed, targetBias: false };
      }
      const attempts = this.bodies.length >= 3 ? 384 : 96;
      for (let attempt = 0; attempt < attempts; attempt += 1) {
        const candidate = (this.physicsSeed + Math.imul(attempt + 1, 0x9e3779b1)) >>> 0;
        if (this._seedMatches(candidate, "tumble")) return { seed: candidate, targetBias: "tumble" };
      }
      // A difficult multi-body combination can statistically miss every
      // ordinary tumble candidate.  Retry from a lower transverse-spin launch
      // that still goes through the same gravity, contacts, bounce and sleep
      // simulation.  This changes only the pre-frame initial state; it never
      // applies corrective forces or rotations to the visible throw.
      for (let attempt = 0; attempt < 192; attempt += 1) {
        const candidate = (this.physicsSeed + Math.imul(attempt + attempts + 1, 0x85ebca6b)) >>> 0;
        if (this._seedMatches(candidate, "conservative")) {
          return { seed: candidate, targetBias: "conservative" };
        }
      }
      for (let attempt = 0; attempt < 24; attempt += 1) {
        const candidate = (this.physicsSeed + Math.imul(attempt + attempts + 193, 0xc2b2ae35)) >>> 0;
        if (this._seedMatches(candidate, "stable")) return { seed: candidate, targetBias: "stable" };
      }
      console.warn("cannon-es replay planner exhausted candidates; using an unconstrained physical throw");
      return { seed: this.physicsSeed, targetBias: false };
    }

    _prepare() {
      if (this._prepared) return;
      const selection = this._selectReplaySeed();
      this.replaySeed = selection.seed;
      this.replayBias = selection.targetBias;
      const populated = this._populateWorld(this.replaySeed, false, this.replayBias);
      this.world = populated.world;
      populated.dynamicBodies.forEach((cannonBody, index) => {
        const wrapper = this.bodies[index];
        wrapper.cannonBody = cannonBody;
        wrapper.finalFace = null;
        wrapper.restTime = 0;
        wrapper.faceStableTime = 0;
        wrapper.settledFaceStableTime = 0;
        wrapper.lastObservedFace = null;
        wrapper.angularTravel = 0;
        wrapper.unstableContactTime = 0;
        wrapper.supportContact = null;
        cannonBody.addEventListener("collide", event => {
          const now = performance.now();
          const impact = event.contact && typeof event.contact.getImpactVelocityAlongNormal === "function"
            ? Math.abs(event.contact.getImpactVelocityAlongNormal())
            : Math.abs(cannonBody.velocity.y);
          if (impact > 20 && now - wrapper.lastBounceAt > 70) {
            wrapper.lastBounceAt = now;
            if (event.body && event.body.userData && event.body.userData.kind === "wall") {
              if (wrapper.onWallHit) wrapper.onWallHit(impact);
            } else if (wrapper.onBounce) {
              wrapper.onBounce(impact);
            }
          }
        });
      });
      this._prepared = true;
      this._settledReported = false;
    }

    _updateSettlement(dt) {
      for (const wrapper of this.bodies) {
        const cannonBody = wrapper.cannonBody;
        if (!cannonBody) continue;
        const face = wrapper.shape === "coin"
          ? coinFaceUpFromQuaternion(wrapper.q)
          : diceFaceUpFromQuaternion(wrapper.q);
        const stableFace = wrapper.shape === "coin" ? face.alignment > 0.985 : face.alignment > 0.955;
        const linearSpeed = cannonBody.velocity.length();
        const angularSpeed = cannonBody.angularVelocity.length();
        wrapper.angularTravel += angularSpeed * dt;
        if (face.value === wrapper.lastObservedFace) wrapper.faceStableTime += dt;
        else {
          wrapper.lastObservedFace = face.value;
          wrapper.faceStableTime = 0;
        }
        if (stableFace && linearSpeed < 4.5 && angularSpeed < 0.75 && diceFloorContact(wrapper).minY < 0.8) {
          wrapper.restTime += dt;
          const requiredRest = wrapper.shape === "coin" ? 0.68 : 0.42;
          if (wrapper.restTime > requiredRest && cannonBody.sleepState !== CANNON.Body.SLEEPING) cannonBody.sleep();
        } else {
          wrapper.restTime = 0;
        }
        if (cannonBody.sleepState === CANNON.Body.SLEEPING && wrapper.finalFace == null) {
          wrapper.finalFace = face.value;
          wrapper.settledFaceStableTime = wrapper.faceStableTime;
          if (wrapper.onSettle) wrapper.onSettle(wrapper.finalFace);
        }
      }
      if (!this._settledReported && this.bodies.length && this.bodies.every(body => body.settled)) {
        this._settledReported = true;
        if (this.onSettled) this.onSettled(this.bodies.map(body => body.finalFace));
      }
    }

    step(dt) {
      this._prepare();
      this.world.step(dt);
      this._updateSettlement(dt);
    }

    start() {
      this.stop();
      this._prepare();
      this.isRunning = true;
      this.lastTime = performance.now();
      let accumulator = 0;
      const loop = now => {
        if (!this.isRunning) return;
        const frameDt = Math.min(0.05, Math.max(0, (now - this.lastTime) / 1000));
        this.lastTime = now;
        accumulator += frameDt;
        let steps = 0;
        while (accumulator >= this.fixedDt && steps < this.maxSubSteps) {
          this.step(this.fixedDt);
          accumulator -= this.fixedDt;
          steps += 1;
        }
        if (steps === this.maxSubSteps && accumulator > this.fixedDt * 2) accumulator = 0;
        this.render();
        if (this.bodies.length && this.bodies.every(body => body.settled)) {
          this.isRunning = false;
          this.render();
          return;
        }
        this.rafId = requestAnimationFrame(loop);
      };
      this.render();
      this.rafId = requestAnimationFrame(loop);
    }

    render() {
      const scaleFactor = 0.052;
      const hasWebGL = Boolean(this.webglEngine && this.webglEngine.isSupported);
      const cameraSin = Math.sin(64 * DEG2RAD);
      const cameraCos = Math.cos(64 * DEG2RAD);
      for (const body of this.bodies) {
        if (!body.cannonBody) continue;
        if (body.threeMesh) {
          const planeRenderY = this.webglEngine ? this.webglEngine.planeY * scaleFactor : 0;
          body.threeMesh.position.set(body.x * scaleFactor, (body.y - this.planeY) * scaleFactor + planeRenderY, body.z * scaleFactor);
          body.threeMesh.quaternion.set(body.q.x, body.q.y, body.q.z, body.q.w);
        }
        if (body.element) {
          const height = body.y - this.planeY;
          const cssY = -cameraSin * height + cameraCos * body.z;
          const cssZ = cameraCos * height + cameraSin * body.z;
          body.element.style.transform = `translate3d(${body.x}px, ${cssY}px, ${cssZ}px) ${diceQuatToCssMatrix3d(body.q)}`;
        }
        if (body.shadowElement) {
          const height = Math.max(0, body.y - this.planeY);
          const scale = Math.max(0.2, 1 - height / 420);
          body.shadowElement.style.transform = `translate3d(${body.x}px, ${cameraCos * body.z}px, 0) scale(${scale})`;
          body.shadowElement.style.opacity = String(Math.max(0.08, body.shadowOpacity * (1 - height / 360)));
        }
      }
      if (hasWebGL) this.webglEngine.render();
    }
  }

  global.StreamThrowPhysics = Object.freeze({
    engine: "cannon-es@0.20.0",
    RigidBody3D,
    StreamPhysicsWorld,
    coinFaceUpFromQuaternion,
    diceDot,
    diceFaceUpFromQuaternion,
    diceFloorContact,
    diceLocalNormalForFace,
    diceQuatToCssMatrix3d,
    diceRotateVector,
    hashSeed,
    seededRandom
  });
})(window);
