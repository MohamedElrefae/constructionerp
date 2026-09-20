/**
 * Civil Engineer Dashboard Client
 *
 * Week 1 Scope: Read-Only inspection and task registration.
 * Plain-Text Plan Rendering Contract:
 * Plans are rendered strictly via DOM textContent.
 * ZERO innerHTML, ZERO markdown rendering.
 */

let currentCsrfToken = "";
let activeTaskId = null;
let pollTimer = null;

function getCookie(name) {
	const value = `; ${document.cookie}`;
	const parts = value.split(`; ${name}=`);
	if (parts.length === 2) return parts.pop().split(";").shift();
	return null;
}

async function ensureCsrfToken() {
	const cookieVal = getCookie("dashboard_csrf");
	if (cookieVal) {
		currentCsrfToken = cookieVal;
		return currentCsrfToken;
	}
	try {
		const res = await fetch("/api/auth/csrf-token", { credentials: "same-origin" });
		if (res.ok) {
			const data = await res.json();
			currentCsrfToken = data.csrf_token;
		}
	} catch (err) {
		console.error("Failed to obtain CSRF token:", err);
	}
	return currentCsrfToken;
}

async function apiFetch(url, options = {}) {
	await ensureCsrfToken();
	const headers = options.headers || {};
	const method = (options.method || "GET").toUpperCase();
	if (["POST", "PUT", "DELETE", "PATCH"].includes(method)) {
		headers["X-CSRF-Token"] = currentCsrfToken;
		if (options.body && typeof options.body === "string" && !headers["Content-Type"]) {
			headers["Content-Type"] = "application/json";
		}
	}
	options.headers = headers;
	options.credentials = "same-origin";
	return fetch(url, options);
}

// ---------------------------------------------------------------------------
// Plan & State Rendering (Plain-Text Contract & Truthful Display)
// ---------------------------------------------------------------------------

function updatePlanDisplay(planData, stateData) {
	const title = document.getElementById("plan-title");
	const container = document.getElementById("plan-display");
	if (!container) return;

	// Truthful labeling based on authoritative plan_granted state
	if (stateData && stateData.plan_granted === true) {
		title.textContent = "Approved Plan";
	} else {
		title.textContent = "Proposed Plan (Pending Approval)";
	}

	// Strict plain-text contract: NEVER assign innerHTML or parse markdown
	container.textContent = planData && planData.plan_text ? planData.plan_text : "";
}

function updateStagesDisplay(stateData) {
	const container = document.getElementById("stages-container");
	if (!container) return;
	container.innerHTML = ""; // Container structure only

	const stages = stateData && stateData.stages ? stateData.stages : {};
	const stageKeys = Object.keys(stages);

	if (stageKeys.length === 0) {
		const p = document.createElement("p");
		p.className = "text-muted";
		p.textContent = "No stages defined.";
		container.appendChild(p);
		return;
	}

	for (const stageName of stageKeys) {
		const stageInfo = stages[stageName];
		const item = document.createElement("div");
		item.className = "stage-item";

		const nameSpan = document.createElement("span");
		nameSpan.className = "stage-name";
		nameSpan.textContent = stageName;
		item.appendChild(nameSpan);

		const statusSpan = document.createElement("span");
		statusSpan.className = "stage-status";

		let statusText = "Unknown";
		let isHistorical = false;
		if (typeof stageInfo === "string") {
			statusText = stageInfo;
		} else if (stageInfo && typeof stageInfo === "object") {
			statusText = stageInfo.status || "Unknown";
			isHistorical = Boolean(stageInfo.historical);
		}

		if (isHistorical) {
			statusText += " (historical)";
		}

		statusSpan.textContent = statusText;
		item.appendChild(statusSpan);
		container.appendChild(item);
	}
}

function updateActiveJobsDisplay(stateData) {
	const container = document.getElementById("jobs-container");
	if (!container) return;
	container.innerHTML = "";

	const jobs = stateData && Array.isArray(stateData.active_jobs) ? stateData.active_jobs : [];

	if (jobs.length === 0) {
		const p = document.createElement("p");
		p.className = "text-muted";
		p.textContent = "No active jobs.";
		container.appendChild(p);
		return;
	}

	for (const job of jobs) {
		const item = document.createElement("div");
		item.className = "job-item";

		const roleSpan = document.createElement("span");
		roleSpan.className = "job-role";
		roleSpan.textContent = job.role ? `Role: ${job.role}` : "Role: Unspecified";
		item.appendChild(roleSpan);

		const statusBadge = document.createElement("span");
		statusBadge.className = "badge";

		// Truthful Active Jobs Fallback:
		// If status is null, undefined, empty, or missing, render strictly as "Unknown".
		// NEVER render as "Pending".
		let statusText = "Unknown";
		if (job && job.status && typeof job.status === "string" && job.status.trim() !== "") {
			statusText = job.status.trim();
			statusBadge.classList.add("badge-active");
		} else {
			statusBadge.classList.add("badge-neutral");
		}

		statusBadge.textContent = statusText;
		item.appendChild(statusBadge);
		container.appendChild(item);
	}
}

function updateNextRolesDisplay(stateData) {
	const container = document.getElementById("next-roles-container");
	if (!container) return;
	container.innerHTML = "";

	const nextRoles = stateData && Array.isArray(stateData.next_roles) ? stateData.next_roles : [];
	if (nextRoles.length === 0) {
		const p = document.createElement("p");
		p.className = "text-muted";
		p.textContent = "None.";
		container.appendChild(p);
		return;
	}

	for (const r of nextRoles) {
		const tag = document.createElement("span");
		tag.className = "tag";
		tag.textContent = r;
		container.appendChild(tag);
	}
}

// Week 2 State Caches
let currentReviewContext = null;
let currentAiContext = null;
let currentPlanData = null;

// Week 3 State Caches
let currentFindingsData = null;
let activeFindingsFilter = "all";
let currentEvidenceList = [];
let currentDiffData = null;
let currentSettingsData = null;
let currentErpData = null;

function updateProposalDisplay(reviewCtx) {
	const details = document.getElementById("proposal-details");
	const btn = document.getElementById("adopt-scope-btn");
	if (!details || !btn) return;

	const proposal = reviewCtx && reviewCtx.proposal;
	if (proposal) {
		details.textContent = JSON.stringify(proposal, null, 2);
		btn.style.display =
			reviewCtx.plan_granted || reviewCtx.current_stage !== "plan" ? "none" : "inline-block";
	} else {
		details.textContent = "No architect scope proposal submitted.";
		btn.style.display = "none";
	}
}

function updateReviewDisplay(reviewCtx, stateData) {
	const details = document.getElementById("review-hashes-details");
	const createBtn = document.getElementById("create-review-btn");
	const approveBtn = document.getElementById("approve-plan-btn");
	if (!details || !createBtn || !approveBtn) return;

	const gate = reviewCtx && reviewCtx.gate;
	const planGranted = Boolean(reviewCtx && reviewCtx.plan_granted);

	if (planGranted) {
		details.textContent = "Status: PLAN GRANTED (Approved)\nNo pending approval gate.";
		createBtn.style.display = "none";
		approveBtn.style.display = "none";
		return;
	}

	if (!gate || gate.scope !== "PLAN") {
		details.textContent = `Pending Gate: ${
			gate ? gate.scope : "None"
		}\nNo pending PLAN approval gate.`;
		createBtn.style.display = "none";
		approveBtn.style.display = "none";
		return;
	}

	const lines = [
		`Gate ID: ${gate.gate_id || "N/A"}`,
		`Stage: ${reviewCtx.current_stage || "N/A"}`,
		`Plan Revision Hash: ${reviewCtx.plan_revision_hash || "N/A"}`,
		`Scope Hash: ${reviewCtx.scope_hash || "N/A"}`,
		`Roles Hash: ${reviewCtx.roles_hash || "N/A"}`,
	];

	const activeReview = reviewCtx.active_review;
	if (activeReview) {
		lines.push("");
		lines.push("--- Active Review Snapshot ---");
		lines.push(`Review ID: ${activeReview.review_id}`);
		lines.push(`Reviewed By: ${activeReview.reviewed_by}`);
		lines.push(`Created: ${activeReview.created_utc}`);
		lines.push(`Fingerprint: ${activeReview.content_fingerprint}`);

		details.textContent = lines.join("\n");
		createBtn.style.display = "none";
		approveBtn.style.display = "inline-block";
		approveBtn.disabled = false;
	} else {
		lines.push("");
		lines.push("--- Review Snapshot Status ---");
		lines.push("No review snapshot created for this gate.");
		lines.push("You must create a review snapshot before approving.");

		details.textContent = lines.join("\n");
		createBtn.style.display = "inline-block";
		approveBtn.style.display = "none";
	}
}

function updateAiContextDisplay(aiCtx) {
	const memEl = document.getElementById("sprint-memory-display");
	if (memEl) {
		memEl.textContent =
			aiCtx && aiCtx.session_memory_md
				? aiCtx.session_memory_md
				: "(Session memory is empty)";
	}

	const tbody = document.getElementById("provenance-tbody");
	if (tbody) {
		tbody.innerHTML = "";
		const prov = aiCtx && Array.isArray(aiCtx.provenance) ? aiCtx.provenance : [];
		for (const item of prov) {
			const tr = document.createElement("tr");

			const tdPath = document.createElement("td");
			tdPath.className = "code-cell";
			tdPath.textContent = item.path;
			tr.appendChild(tdPath);

			const tdMandatory = document.createElement("td");
			tdMandatory.textContent = item.is_mandatory ? "Mandatory" : "Optional";
			tr.appendChild(tdMandatory);

			const tdStatus = document.createElement("td");
			const badge = document.createElement("span");
			badge.className = "badge " + (item.exists ? "badge-success" : "badge-neutral");
			badge.textContent = item.exists ? "PRESENT" : "MISSING";
			tdStatus.appendChild(badge);
			tr.appendChild(tdStatus);

			const tdSha = document.createElement("td");
			tdSha.className = "code-cell";
			tdSha.textContent = item.sha256 ? item.sha256.substring(0, 16) + "..." : "N/A";
			tr.appendChild(tdSha);

			tbody.appendChild(tr);
		}
	}
}

// ---------------------------------------------------------------------------
// Week 3 Inspection & Projection Functions
// ---------------------------------------------------------------------------

async function loadEvidenceList() {
	if (!activeTaskId) return;
	const tbody = document.getElementById("evidence-tbody");
	const msg = document.getElementById("evidence-msg");
	if (msg) msg.style.display = "none";
	if (!tbody) return;

	try {
		const res = await apiFetch(`/api/tasks/${encodeURIComponent(activeTaskId)}/evidence`);
		if (!res.ok) {
			if (msg) {
				msg.className = "alert alert-error";
				msg.textContent = "Failed to load evidence list";
				msg.style.display = "block";
			}
			return;
		}
		const data = await res.json();
		currentEvidenceList = data.files || [];
		tbody.innerHTML = "";

		if (currentEvidenceList.length === 0) {
			const tr = document.createElement("tr");
			const td = document.createElement("td");
			td.colSpan = 4;
			td.className = "empty-state";
			td.textContent = "No evidence files found for this worktree.";
			tr.appendChild(td);
			tbody.appendChild(tr);
			return;
		}

		for (const file of currentEvidenceList) {
			const tr = document.createElement("tr");

			const tdName = document.createElement("td");
			tdName.textContent = file.filename;
			tr.appendChild(tdName);

			const tdSize = document.createElement("td");
			tdSize.textContent =
				typeof file.size_bytes === "number"
					? file.size_bytes.toLocaleString()
					: file.size_bytes || "-";
			tr.appendChild(tdSize);

			const tdTime = document.createElement("td");
			tdTime.textContent = file.modified_utc || "-";
			tr.appendChild(tdTime);

			const tdAction = document.createElement("td");
			const viewBtn = document.createElement("button");
			viewBtn.className = "btn btn-small btn-secondary";
			viewBtn.textContent = "View";
			viewBtn.onclick = () => viewEvidenceFile(file.filename);
			tdAction.appendChild(viewBtn);
			tr.appendChild(tdAction);

			tbody.appendChild(tr);
		}
	} catch (err) {
		console.error("Failed to load evidence list:", err);
	}
}

async function viewEvidenceFile(filename) {
	if (!activeTaskId) return;
	const panel = document.getElementById("evidence-viewer-panel");
	const title = document.getElementById("evidence-viewer-title");
	const display = document.getElementById("evidence-display");
	const shaBadge = document.getElementById("evidence-sha-badge");
	const truncBadge = document.getElementById("evidence-trunc-badge");
	const msg = document.getElementById("evidence-msg");
	if (msg) msg.style.display = "none";

	try {
		const res = await apiFetch(
			`/api/tasks/${encodeURIComponent(activeTaskId)}/evidence/${encodeURIComponent(
				filename
			)}`
		);
		if (!res.ok) {
			const data = await res.json().catch(() => ({}));
			if (msg) {
				msg.className = "alert alert-error";
				msg.textContent = data.detail || `Failed to read evidence: HTTP ${res.status}`;
				msg.style.display = "block";
			}
			if (panel) panel.style.display = "none";
			return;
		}
		const data = await res.json();
		if (panel) panel.style.display = "block";
		if (title) title.textContent = `Evidence: ${filename}`;
		if (display) display.textContent = data.content || "";
		if (shaBadge) {
			shaBadge.textContent = data.sha256
				? `SHA-256: ${data.sha256.substring(0, 16)}...`
				: "SHA-256: N/A";
		}
		if (truncBadge) {
			truncBadge.style.display = data.truncated ? "inline-block" : "none";
		}
	} catch (err) {
		console.error("Failed to view evidence file:", err);
	}
}

async function loadFindings() {
	if (!activeTaskId) return;
	try {
		const res = await apiFetch(`/api/tasks/${encodeURIComponent(activeTaskId)}/findings`);
		if (!res.ok) return;
		const data = await res.json();
		currentFindingsData = data;
		updateFindingsDisplay();
	} catch (err) {
		console.error("Failed to load findings:", err);
	}
}

function updateFindingsDisplay() {
	if (!currentFindingsData) return;
	const stats = currentFindingsData.stats || {};
	const blockingEl = document.getElementById("blocking-count-badge");
	const totalEl = document.getElementById("total-findings-badge");
	const backlogEl = document.getElementById("backlog-count-badge");

	if (blockingEl) blockingEl.textContent = `${stats.blocking_findings || 0} Blocking Defects`;
	if (totalEl) totalEl.textContent = `${stats.total_findings || 0} Total Findings`;
	if (backlogEl) backlogEl.textContent = `${stats.backlog_items || 0} Backlog Items`;

	const container = document.getElementById("findings-list");
	if (!container) return;
	container.innerHTML = "";

	const findings = currentFindingsData.findings || [];
	const backlog = currentFindingsData.backlog || [];

	let itemsToRender = [];
	if (activeFindingsFilter === "all") {
		itemsToRender = [
			...findings.map((f) => ({ ...f, _type: "finding" })),
			...backlog.map((b) => ({ ...b, _type: "backlog" })),
		];
	} else if (activeFindingsFilter === "blocking") {
		itemsToRender = findings
			.filter(
				(f) =>
					["implementation_defect", "design_defect"].includes(f.classification) ||
					["BLOCKING", "HIGH"].includes(String(f.severity || "").toUpperCase())
			)
			.map((f) => ({ ...f, _type: "finding" }));
	} else if (activeFindingsFilter === "backlog") {
		itemsToRender = backlog.map((b) => ({ ...b, _type: "backlog" }));
	} else if (activeFindingsFilter === "implementation_defect") {
		itemsToRender = findings
			.filter((f) => f.classification === "implementation_defect")
			.map((f) => ({ ...f, _type: "finding" }));
	} else if (activeFindingsFilter === "design_defect") {
		itemsToRender = findings
			.filter((f) => f.classification === "design_defect")
			.map((f) => ({ ...f, _type: "finding" }));
	}

	if (itemsToRender.length === 0) {
		const p = document.createElement("p");
		p.className = "empty-state";
		p.textContent = "No items match the selected filter.";
		container.appendChild(p);
		return;
	}

	for (const item of itemsToRender) {
		const card = document.createElement("div");
		card.className = "finding-card";
		if (item._type === "backlog") {
			card.classList.add("backlog");
		} else if (
			["implementation_defect", "design_defect"].includes(item.classification) ||
			["BLOCKING", "HIGH"].includes(String(item.severity || "").toUpperCase())
		) {
			card.classList.add("blocking");
		}

		const header = document.createElement("div");
		header.className = "finding-header";

		const title = document.createElement("span");
		title.className = "finding-title";
		title.textContent =
			item.id ||
			item.finding_id ||
			item.item_id ||
			item.title ||
			(item._type === "backlog" ? "Backlog Item" : "Finding");
		header.appendChild(title);

		const badge = document.createElement("span");
		badge.className = "badge";
		if (item._type === "backlog") {
			badge.className += " badge-secondary";
			badge.textContent = "BACKLOG";
		} else {
			const sev = String(item.severity || item.classification || "INFO").toUpperCase();
			if (
				["BLOCKING", "HIGH"].includes(sev) ||
				["implementation_defect", "design_defect"].includes(item.classification)
			) {
				badge.className += " badge-error";
			} else {
				badge.className += " badge-info";
			}
			badge.textContent = item.classification || item.severity || "FINDING";
		}
		header.appendChild(badge);
		card.appendChild(header);

		const body = document.createElement("div");
		body.className = "finding-body";
		body.textContent =
			item.description ||
			item.detail ||
			item.summary ||
			(typeof item === "string" ? item : JSON.stringify(item, null, 2));
		card.appendChild(body);

		const meta = document.createElement("div");
		meta.className = "finding-meta";
		if (item.stage) {
			const sSpan = document.createElement("span");
			sSpan.textContent = `Stage: ${item.stage}`;
			meta.appendChild(sSpan);
		}
		if (item.role) {
			const rSpan = document.createElement("span");
			rSpan.textContent = `Role: ${item.role}`;
			meta.appendChild(rSpan);
		}
		if (item.created_utc || item.timestamp) {
			const tSpan = document.createElement("span");
			tSpan.textContent = `Date: ${item.created_utc || item.timestamp}`;
			meta.appendChild(tSpan);
		}
		if (meta.childNodes.length > 0) {
			card.appendChild(meta);
		}

		container.appendChild(card);
	}
}

async function loadDiff() {
	if (!activeTaskId) return;
	try {
		const res = await apiFetch(`/api/tasks/${encodeURIComponent(activeTaskId)}/diff`);
		if (!res.ok) return;
		const data = await res.json();
		currentDiffData = data;
		updateDiffDisplay(data);
	} catch (err) {
		console.error("Failed to load diff:", err);
	}
}

function updateDiffDisplay(data) {
	if (!data) return;
	const baseBadge = document.getElementById("diff-base-badge");
	const headBadge = document.getElementById("diff-head-badge");
	const truncBadge = document.getElementById("diff-trunc-badge");
	const countEl = document.getElementById("diff-files-count");
	const filesList = document.getElementById("diff-files-list");
	const display = document.getElementById("diff-display");

	if (baseBadge)
		baseBadge.textContent = `Base: ${
			data.base_commit ? data.base_commit.substring(0, 8) : "None"
		}`;
	if (headBadge)
		headBadge.textContent = `HEAD: ${
			data.head_commit ? data.head_commit.substring(0, 8) : "HEAD"
		}`;
	if (truncBadge) truncBadge.style.display = data.truncated ? "inline-block" : "none";

	const files = data.files || [];
	if (countEl) countEl.textContent = files.length;
	if (filesList) {
		filesList.innerHTML = "";
		if (files.length === 0) {
			const span = document.createElement("span");
			span.className = "text-muted";
			span.textContent = "No changed files.";
			filesList.appendChild(span);
		} else {
			for (const f of files) {
				const tag = document.createElement("span");
				tag.className = "tag";
				tag.textContent = `${f.status} ${f.path}`;
				filesList.appendChild(tag);
			}
		}
	}

	if (display) {
		display.innerHTML = "";
		const diffText = data.diff_text || "";
		if (!diffText.trim()) {
			display.textContent = "No changes detected against base commit.";
			return;
		}

		const lines = diffText.split("\n");
		for (const line of lines) {
			const span = document.createElement("span");
			if (line.startsWith("+") && !line.startsWith("+++")) {
				span.className = "diff-line-add";
			} else if (line.startsWith("-") && !line.startsWith("---")) {
				span.className = "diff-line-del";
			} else if (line.startsWith("@@") || line.startsWith("diff --git")) {
				span.className = "diff-line-hdr";
			}
			span.textContent = line + "\n";
			display.appendChild(span);
		}
	}
}

async function loadSettings() {
	if (!activeTaskId) return;
	try {
		const res = await apiFetch(`/api/tasks/${encodeURIComponent(activeTaskId)}/settings`);
		if (!res.ok) return;
		const data = await res.json();
		currentSettingsData = data;
		updateSettingsDisplay(data);
	} catch (err) {
		console.error("Failed to load settings:", err);
	}
}

function updateSettingsDisplay(data) {
	if (!data) return;
	const tbody = document.getElementById("settings-roles-tbody");
	if (tbody) {
		tbody.innerHTML = "";
		const roles = data.roles || {};
		const roleKeys = Object.keys(roles);
		if (roleKeys.length === 0) {
			const tr = document.createElement("tr");
			const td = document.createElement("td");
			td.colSpan = 6;
			td.className = "empty-state";
			td.textContent = "No roles configured.";
			tr.appendChild(td);
			tbody.appendChild(tr);
		} else {
			for (const rName of roleKeys) {
				const r = roles[rName] || {};
				const tr = document.createElement("tr");

				const tdRole = document.createElement("td");
				tdRole.textContent = rName;
				tr.appendChild(tdRole);

				const tdTool = document.createElement("td");
				tdTool.textContent = r.tool || "-";
				tr.appendChild(tdTool);

				const tdModel = document.createElement("td");
				tdModel.textContent = r.model || "-";
				tr.appendChild(tdModel);

				const tdEffort = document.createElement("td");
				tdEffort.textContent = r.effort || "-";
				tr.appendChild(tdEffort);

				const tdVersion = document.createElement("td");
				tdVersion.textContent = r.version || "-";
				tr.appendChild(tdVersion);

				const tdSha = document.createElement("td");
				tdSha.className = "code-cell";
				tdSha.textContent = r.prompt_sha256
					? r.prompt_sha256.substring(0, 16) + "..."
					: "N/A";
				tr.appendChild(tdSha);

				tbody.appendChild(tr);
			}
		}
	}

	const esc = data.escalation_status || {};
	const blockersEl = document.getElementById("settings-consecutive-blockers");
	const cyclesEl = document.getElementById("settings-cycles-in-stage");
	const attemptsEl = document.getElementById("settings-stage-attempts");
	const pauseEl = document.getElementById("settings-pause-reason");

	if (blockersEl) blockersEl.textContent = esc.consecutive_blockers ?? 0;
	if (cyclesEl) cyclesEl.textContent = esc.cycles_in_stage ?? 0;
	if (attemptsEl) attemptsEl.textContent = esc.stage_attempts ?? 1;
	if (pauseEl) pauseEl.textContent = esc.pause_reason || "None";

	const timeouts = data.timeouts || {};
	const softEl = document.getElementById("settings-soft-timeout");
	const hardEl = document.getElementById("settings-hard-timeout");
	if (softEl) softEl.textContent = timeouts.soft_timeout ?? 2700;
	if (hardEl) hardEl.textContent = timeouts.hard_timeout ?? 3600;
}

async function loadErpStatus() {
	try {
		const res = await apiFetch("/api/erp/projection");
		if (!res.ok) {
			const data = await res.json().catch(() => ({}));
			showErpError(data.detail || `HTTP ${res.status}`);
			return;
		}
		const data = await res.json();
		currentErpData = data;
		updateErpDisplay(data);
	} catch (err) {
		console.error("Failed to load ERP status:", err);
		showErpError("Failed to fetch Stage 4 ERP projection");
	}
}

function showErpError(errMsg) {
	const statusBadge = document.getElementById("erp-status-badge");
	const integBadge = document.getElementById("erp-integrity-badge");
	const warningsDiv = document.getElementById("erp-integrity-warnings");

	if (statusBadge) statusBadge.textContent = "UNAVAILABLE";
	if (integBadge) {
		integBadge.className = "badge badge-error";
		integBadge.textContent = "ERROR";
	}
	if (warningsDiv) {
		warningsDiv.textContent = errMsg;
		warningsDiv.style.display = "block";
	}
}

function updateErpDisplay(data) {
	if (!data) return;
	const statusBadge = document.getElementById("erp-status-badge");
	const integBadge = document.getElementById("erp-integrity-badge");
	const warningsDiv = document.getElementById("erp-integrity-warnings");

	if (statusBadge) {
		statusBadge.textContent = data.status || "PARKED";
		statusBadge.className = "badge badge-warning";
	}

	if (integBadge) {
		const isVerified = data.integrity_status === "verified";
		integBadge.className = "badge " + (isVerified ? "badge-success" : "badge-warning");
		integBadge.textContent = (data.integrity_status || "UNKNOWN").toUpperCase();
	}

	const setEl = (id, val) => {
		const el = document.getElementById(id);
		if (el) el.textContent = val !== undefined && val !== null ? val : "-";
	};

	setEl("erp-company", data.company);
	setEl("erp-domain", data.domain);
	setEl("erp-export-file", data.export_file);
	setEl("erp-rows", data.rows);
	setEl("erp-groups", data.groups);
	setEl("erp-leaves", data.leaves);
	setEl("erp-recorded-utc", data.recorded_utc);

	setEl("erp-permissions", data.permissions);
	setEl("erp-manifest-sha256", data.manifest_sha256);
	setEl("erp-dataset-sha256", data.export_sha256);
	setEl("erp-masked-path", data.masked_export_path);

	if (warningsDiv) {
		const warnings = data.warnings || [];
		if (warnings.length > 0) {
			warningsDiv.innerHTML = "";
			for (const w of warnings) {
				const p = document.createElement("p");
				p.textContent = `Warning: ${w}`;
				warningsDiv.appendChild(p);
			}
			warningsDiv.style.display = "block";
		} else {
			warningsDiv.style.display = "none";
		}
	}
}

function loadTabContent(tabId) {
	if (tabId === "tab-evidence") {
		loadEvidenceList();
	} else if (tabId === "tab-findings") {
		loadFindings();
	} else if (tabId === "tab-diff") {
		loadDiff();
	} else if (tabId === "tab-settings") {
		loadSettings();
	} else if (tabId === "tab-erp") {
		loadErpStatus();
	}
}

async function downloadExport(endpoint, fallbackFilename) {
	if (!activeTaskId) return;
	try {
		const res = await apiFetch(`/api/tasks/${encodeURIComponent(activeTaskId)}/${endpoint}`);
		if (!res.ok) {
			alert(`Export failed: HTTP ${res.status}`);
			return;
		}
		const disposition = res.headers.get("Content-Disposition");
		let filename = fallbackFilename;
		if (disposition && disposition.includes("filename=")) {
			const match = disposition.match(/filename="?([^"]+)"?/);
			if (match) filename = match[1];
		}
		const blob = await res.blob();
		const url = window.URL.createObjectURL(blob);
		const a = document.createElement("a");
		a.href = url;
		a.download = filename;
		document.body.appendChild(a);
		a.click();
		window.URL.revokeObjectURL(url);
		document.body.removeChild(a);
	} catch (err) {
		console.error("Export download error:", err);
		alert("Export download error: " + err.message);
	}
}

// ---------------------------------------------------------------------------
// Task Detail Loading & Polling
// ---------------------------------------------------------------------------

async function inspectTask(taskId) {
	activeTaskId = taskId;
	const detailSection = document.getElementById("task-detail-section");
	detailSection.style.display = "block";
	detailSection.scrollIntoView({ behavior: "smooth" });

	await refreshTaskDetail();

	const activeTab = document.querySelector(".tab-btn.active");
	if (activeTab) {
		loadTabContent(activeTab.getAttribute("data-tab"));
	}

	if (pollTimer) clearInterval(pollTimer);
	pollTimer = setInterval(refreshTaskDetail, 3000);
}

async function refreshTaskDetail() {
	if (!activeTaskId) return;

	try {
		const [stateRes, planRes, reviewRes, aiRes] = await Promise.all([
			apiFetch(`/api/tasks/${encodeURIComponent(activeTaskId)}/state`),
			apiFetch(`/api/tasks/${encodeURIComponent(activeTaskId)}/plan`),
			apiFetch(`/api/tasks/${encodeURIComponent(activeTaskId)}/review-context`),
			apiFetch(`/api/tasks/${encodeURIComponent(activeTaskId)}/ai-context`),
		]);

		if (stateRes.ok && planRes.ok) {
			const stateData = await stateRes.json();
			const planData = await planRes.json();
			currentPlanData = planData;

			document.getElementById("detail-task-id").textContent = `Task: ${activeTaskId}`;
			document.getElementById("detail-branch-badge").textContent =
				stateData.branch || "Unknown Branch";
			document.getElementById("detail-status-badge").textContent =
				stateData.status || "UNKNOWN";

			updateStagesDisplay(stateData);
			updateActiveJobsDisplay(stateData);
			updateNextRolesDisplay(stateData);
			updatePlanDisplay(planData, stateData);

			if (reviewRes.ok) {
				const reviewCtx = await reviewRes.json();
				currentReviewContext = reviewCtx;
				updateProposalDisplay(reviewCtx);
				updateReviewDisplay(reviewCtx, stateData);
			}

			if (aiRes.ok) {
				const aiCtx = await aiRes.json();
				currentAiContext = aiCtx;
				updateAiContextDisplay(aiCtx);
			}

			const activeTab = document.querySelector(".tab-btn.active");
			if (activeTab) {
				const tabId = activeTab.getAttribute("data-tab");
				if (["tab-evidence", "tab-findings", "tab-diff", "tab-settings"].includes(tabId)) {
					loadTabContent(tabId);
				}
			}
		}
	} catch (err) {
		console.error("Failed refreshing task detail:", err);
	}
}

// ---------------------------------------------------------------------------
// Task Registration & Listing
// ---------------------------------------------------------------------------

async function loadTasks() {
	try {
		const res = await apiFetch("/api/tasks");
		if (!res.ok) {
			if (res.status === 401) {
				showAuth(false);
			}
			return;
		}
		const tasks = await res.json();
		const tbody = document.getElementById("tasks-tbody");
		const noTasksMsg = document.getElementById("no-tasks-msg");
		tbody.innerHTML = "";

		if (!tasks || tasks.length === 0) {
			noTasksMsg.style.display = "block";
			return;
		}
		noTasksMsg.style.display = "none";

		for (const t of tasks) {
			const tr = document.createElement("tr");

			const tdId = document.createElement("td");
			tdId.textContent = t.task_id;
			tr.appendChild(tdId);

			const tdWork = document.createElement("td");
			tdWork.textContent = t.work_item;
			tr.appendChild(tdWork);

			const tdBranch = document.createElement("td");
			tdBranch.textContent = t.task_branch;
			tr.appendChild(tdBranch);

			const tdStatus = document.createElement("td");
			const statusBadge = document.createElement("span");
			statusBadge.className = "badge";
			statusBadge.textContent = t.cached_status || "UNKNOWN";
			tdStatus.appendChild(statusBadge);
			tr.appendChild(tdStatus);

			const tdStage = document.createElement("td");
			tdStage.textContent = t.cached_stage || "plan";
			tr.appendChild(tdStage);

			const tdActions = document.createElement("td");
			const inspectBtn = document.createElement("button");
			inspectBtn.className = "btn btn-small btn-primary";
			inspectBtn.textContent = "Inspect";
			inspectBtn.onclick = () => inspectTask(t.task_id);
			tdActions.appendChild(inspectBtn);

			const unregisterBtn = document.createElement("button");
			unregisterBtn.className = "btn btn-small btn-secondary";
			unregisterBtn.textContent = "Unregister";
			unregisterBtn.style.marginLeft = "8px";
			unregisterBtn.onclick = async () => {
				if (confirm(`Unregister task ${t.task_id}?`)) {
					const delRes = await apiFetch(`/api/tasks/${encodeURIComponent(t.task_id)}`, {
						method: "DELETE",
					});
					if (delRes.ok) {
						if (activeTaskId === t.task_id) {
							activeTaskId = null;
							document.getElementById("task-detail-section").style.display = "none";
							if (pollTimer) clearInterval(pollTimer);
						}
						loadTasks();
					}
				}
			};
			tdActions.appendChild(unregisterBtn);

			tr.appendChild(tdActions);
			tbody.appendChild(tr);
		}
	} catch (err) {
		console.error("Error loading tasks:", err);
	}
}

// ---------------------------------------------------------------------------
// Authentication & Session Handlers
// ---------------------------------------------------------------------------

function showAuth(authenticated, username = "", mustChangePassword = false) {
	const authSection = document.getElementById("auth-section");
	const setupSection = document.getElementById("setup-password-section");
	const mainContent = document.getElementById("main-content");
	const userControls = document.getElementById("user-controls");
	const navUsername = document.getElementById("nav-username");

	if (authenticated) {
		authSection.style.display = "none";
		userControls.style.display = "flex";
		navUsername.textContent = username;

		if (mustChangePassword) {
			setupSection.style.display = "block";
			mainContent.style.display = "none";
		} else {
			setupSection.style.display = "none";
			mainContent.style.display = "block";
			loadTasks();
		}
	} else {
		authSection.style.display = "block";
		setupSection.style.display = "none";
		mainContent.style.display = "none";
		userControls.style.display = "none";
		navUsername.textContent = "";
		if (pollTimer) clearInterval(pollTimer);
	}
}

async function checkAuthStatus() {
	try {
		const res = await apiFetch("/api/auth/me");
		if (res.ok) {
			const data = await res.json();
			if (data.authenticated) {
				showAuth(true, data.username, Boolean(data.must_change_password));
				return;
			}
		}
	} catch (err) {
		console.warn("Auth check failed:", err);
	}
	showAuth(false);
}

// ---------------------------------------------------------------------------
// DOM Event Listeners
// ---------------------------------------------------------------------------

let activeLoginUsername = "";

document.addEventListener("DOMContentLoaded", async () => {
	await ensureCsrfToken();
	await checkAuthStatus();

	// Login Form
	const loginForm = document.getElementById("login-form");
	loginForm.addEventListener("submit", async (e) => {
		e.preventDefault();
		const errorDiv = document.getElementById("login-error");
		errorDiv.style.display = "none";

		const username = document.getElementById("login-username").value;
		const password = document.getElementById("login-password").value;
		activeLoginUsername = username;

		try {
			const res = await apiFetch("/api/auth/login", {
				method: "POST",
				body: JSON.stringify({ username, password }),
			});
			const data = await res.json();
			if (res.ok && data.ok) {
				currentCsrfToken = data.csrf_token;
				if (data.must_change_password) {
					document.getElementById("setup-current-password").value = password;
					showAuth(true, data.username, true);
				} else {
					showAuth(true, data.username, false);
				}
			} else {
				errorDiv.textContent = data.detail || "Login failed";
				errorDiv.style.display = "block";
			}
		} catch (err) {
			errorDiv.textContent = "Network or server error during login";
			errorDiv.style.display = "block";
		}
	});

	// Setup Password Form (First-Run Permanent Password)
	const setupForm = document.getElementById("setup-password-form");
	setupForm.addEventListener("submit", async (e) => {
		e.preventDefault();
		const errorDiv = document.getElementById("setup-password-error");
		errorDiv.style.display = "none";

		const current_password = document.getElementById("setup-current-password").value;
		const new_password = document.getElementById("setup-new-password").value;

		if (new_password.length < 12) {
			errorDiv.textContent = "New permanent password must be at least 12 characters long";
			errorDiv.style.display = "block";
			return;
		}
		if (new_password === current_password) {
			errorDiv.textContent =
				"New permanent password must be different from current password";
			errorDiv.style.display = "block";
			return;
		}

		try {
			const res = await apiFetch("/api/auth/setup-password", {
				method: "POST",
				body: JSON.stringify({ current_password, new_password }),
			});
			const data = await res.json();
			if (res.ok && data.ok) {
				showAuth(true, activeLoginUsername || "engineer", false);
			} else {
				errorDiv.textContent = data.detail || "Failed to set permanent password";
				errorDiv.style.display = "block";
			}
		} catch (err) {
			errorDiv.textContent = "Network or server error setting permanent password";
			errorDiv.style.display = "block";
		}
	});

	// Logout Button
	document.getElementById("logout-btn").addEventListener("click", async () => {
		try {
			await apiFetch("/api/auth/logout", { method: "POST" });
		} finally {
			showAuth(false);
		}
	});

	// Register Form
	const regForm = document.getElementById("register-form");
	regForm.addEventListener("submit", async (e) => {
		e.preventDefault();
		const msgDiv = document.getElementById("register-message");
		msgDiv.style.display = "none";

		const pathInput = document.getElementById("worktree-path-input");
		const worktree_path = pathInput.value.trim();
		if (!worktree_path) return;

		try {
			const res = await apiFetch("/api/tasks/register", {
				method: "POST",
				body: JSON.stringify({ worktree_path }),
			});
			const data = await res.json();
			if (res.ok && data.ok) {
				msgDiv.className = "alert alert-success";
				msgDiv.textContent = `Worktree registered successfully: ${data.task.task_id}`;
				msgDiv.style.display = "block";
				pathInput.value = "";
				loadTasks();
			} else {
				msgDiv.className = "alert alert-error";
				msgDiv.textContent = data.detail || "Failed to register worktree";
				msgDiv.style.display = "block";
			}
		} catch (err) {
			msgDiv.className = "alert alert-error";
			msgDiv.textContent = "Server error during registration";
			msgDiv.style.display = "block";
		}
	});

	// Tab Navigation Listeners
	document.querySelectorAll(".tab-btn").forEach((btn) => {
		btn.addEventListener("click", () => {
			document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
			document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
			btn.classList.add("active");
			const targetId = btn.getAttribute("data-tab");
			const targetEl = document.getElementById(targetId);
			if (targetEl) targetEl.classList.add("active");
			loadTabContent(targetId);
		});
	});

	// Bootstrap Form
	const bootstrapForm = document.getElementById("bootstrap-form");
	if (bootstrapForm) {
		bootstrapForm.addEventListener("submit", async (e) => {
			e.preventDefault();
			const msgDiv = document.getElementById("bootstrap-message");
			msgDiv.style.display = "none";
			const submitBtn = document.getElementById("bootstrap-btn");
			submitBtn.disabled = true;

			const workItem = document.getElementById("bootstrap-work-item").value.trim();
			const userBrief = document.getElementById("bootstrap-user-brief").value.trim();
			const baseRef = (document.getElementById("bootstrap-base-ref").value || "HEAD").trim();

			try {
				const res = await apiFetch("/api/tasks/bootstrap", {
					method: "POST",
					body: JSON.stringify({
						work_item: workItem,
						user_brief: userBrief,
						base_ref: baseRef,
					}),
				});
				const data = await res.json();
				if (res.ok && data.ok) {
					msgDiv.className = "alert alert-success";
					msgDiv.textContent = `Task bootstrapped successfully: ${data.task.task_id}`;
					msgDiv.style.display = "block";
					document.getElementById("bootstrap-work-item").value = "";
					document.getElementById("bootstrap-user-brief").value = "";
					await loadTasks();
					inspectTask(data.task.task_id);
				} else {
					msgDiv.className = "alert alert-error";
					msgDiv.textContent = data.detail || "Bootstrap failed";
					msgDiv.style.display = "block";
				}
			} catch (err) {
				msgDiv.className = "alert alert-error";
				msgDiv.textContent = "Server error during task bootstrap";
				msgDiv.style.display = "block";
			} finally {
				submitBtn.disabled = false;
			}
		});
	}

	// Adopt Scope Proposal Button
	const adoptBtn = document.getElementById("adopt-scope-btn");
	if (adoptBtn) {
		adoptBtn.addEventListener("click", async () => {
			if (!activeTaskId || !currentReviewContext || !currentReviewContext.proposal) return;
			const msgDiv = document.getElementById("adopt-scope-msg");
			msgDiv.style.display = "none";
			adoptBtn.disabled = true;

			const proposal = currentReviewContext.proposal;
			try {
				const res = await apiFetch(
					`/api/tasks/${encodeURIComponent(activeTaskId)}/adopt-scope`,
					{
						method: "POST",
						body: JSON.stringify({
							scope: proposal.scope,
							implementation_stages: proposal.implementation_stages,
						}),
					}
				);
				const data = await res.json();
				if (res.ok && data.ok) {
					msgDiv.className = "alert alert-success";
					msgDiv.textContent = "Scope proposal adopted successfully.";
					msgDiv.style.display = "block";
					await refreshTaskDetail();
				} else {
					msgDiv.className = "alert alert-error";
					msgDiv.textContent = data.detail || "Failed to adopt scope proposal";
					msgDiv.style.display = "block";
				}
			} catch (err) {
				msgDiv.className = "alert alert-error";
				msgDiv.textContent = "Server error during scope adoption";
				msgDiv.style.display = "block";
			} finally {
				adoptBtn.disabled = false;
			}
		});
	}

	// Create Review Snapshot Button
	const createReviewBtn = document.getElementById("create-review-btn");
	if (createReviewBtn) {
		createReviewBtn.addEventListener("click", async () => {
			if (!activeTaskId || !currentReviewContext || !currentReviewContext.gate) return;
			const msgDiv = document.getElementById("approval-msg");
			msgDiv.style.display = "none";
			createReviewBtn.disabled = true;

			const gate = currentReviewContext.gate;
			const planText =
				currentPlanData && currentPlanData.plan_text ? currentPlanData.plan_text : "";
			const scopeHash = currentReviewContext.scope_hash || "";
			const rolesHash = currentReviewContext.roles_hash || "";

			// Compute sha256 fingerprint of planText + scopeHash + rolesHash
			const encoder = new TextEncoder();
			const dataToHash = encoder.encode(planText + scopeHash + rolesHash);
			const hashBuffer = await crypto.subtle.digest("SHA-256", dataToHash);
			const hashArray = Array.from(new Uint8Array(hashBuffer));
			const fingerprint = hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");

			try {
				const res = await apiFetch(
					`/api/tasks/${encodeURIComponent(activeTaskId)}/create-review`,
					{
						method: "POST",
						body: JSON.stringify({
							gate_id: gate.gate_id,
							plan_revision_hash: currentReviewContext.plan_revision_hash,
							scope_hash: scopeHash,
							roles_hash: rolesHash,
							content_fingerprint: fingerprint,
						}),
					}
				);
				const data = await res.json();
				if (res.ok && data.ok) {
					msgDiv.className = "alert alert-success";
					msgDiv.textContent = `Review snapshot created: ${data.review.review_id}`;
					msgDiv.style.display = "block";
					await refreshTaskDetail();
				} else {
					msgDiv.className = "alert alert-error";
					msgDiv.textContent = data.detail || "Failed to create review snapshot";
					msgDiv.style.display = "block";
				}
			} catch (err) {
				msgDiv.className = "alert alert-error";
				msgDiv.textContent = "Server error creating review snapshot";
				msgDiv.style.display = "block";
			} finally {
				createReviewBtn.disabled = false;
			}
		});
	}

	// Approve Plan Button
	const approveBtn = document.getElementById("approve-plan-btn");
	if (approveBtn) {
		approveBtn.addEventListener("click", async () => {
			if (!activeTaskId) return;
			const msgDiv = document.getElementById("approval-msg");
			msgDiv.style.display = "none";
			approveBtn.disabled = true;

			try {
				const res = await apiFetch(
					`/api/tasks/${encodeURIComponent(activeTaskId)}/approve-plan`,
					{
						method: "POST",
						body: JSON.stringify({}),
					}
				);
				const data = await res.json();
				if (res.ok && data.ok) {
					msgDiv.className = "alert alert-success";
					msgDiv.textContent = "Plan approved successfully.";
					msgDiv.style.display = "block";
					await refreshTaskDetail();
					loadTasks();
				} else {
					msgDiv.className = "alert alert-error";
					msgDiv.textContent = data.detail || "Failed to approve plan";
					msgDiv.style.display = "block";
				}
			} catch (err) {
				msgDiv.className = "alert alert-error";
				msgDiv.textContent = "Server error during plan approval";
				msgDiv.style.display = "block";
			} finally {
				approveBtn.disabled = false;
			}
		});
	}

	// Copy Sprint Memory Button
	const copyMemBtn = document.getElementById("copy-memory-btn");
	if (copyMemBtn) {
		copyMemBtn.addEventListener("click", async () => {
			const memEl = document.getElementById("sprint-memory-display");
			const msgDiv = document.getElementById("copy-memory-msg");
			if (!memEl || !msgDiv) return;

			try {
				await navigator.clipboard.writeText(memEl.textContent || "");
				msgDiv.className = "alert alert-success";
				msgDiv.textContent = "Sprint memory copied to clipboard.";
				msgDiv.style.display = "block";
				setTimeout(() => {
					msgDiv.style.display = "none";
				}, 3000);
			} catch (err) {
				msgDiv.className = "alert alert-error";
				msgDiv.textContent = "Failed to copy to clipboard.";
				msgDiv.style.display = "block";
			}
		});
	}

	// Refresh Tasks Button
	document.getElementById("refresh-tasks-btn").addEventListener("click", () => {
		loadTasks();
	});

	// Findings Filter Buttons
	document.querySelectorAll(".filter-btn").forEach((btn) => {
		btn.addEventListener("click", () => {
			document.querySelectorAll(".filter-btn").forEach((b) => b.classList.remove("active"));
			btn.classList.add("active");
			activeFindingsFilter = btn.getAttribute("data-filter") || "all";
			updateFindingsDisplay();
		});
	});

	// Refresh Evidence Button
	const refreshEvidenceBtn = document.getElementById("refresh-evidence-btn");
	if (refreshEvidenceBtn) {
		refreshEvidenceBtn.addEventListener("click", () => {
			loadEvidenceList();
		});
	}

	// Export Dropdown & Links
	const exportBtn = document.getElementById("export-menu-btn");
	const exportMenu = document.getElementById("export-menu");
	if (exportBtn && exportMenu) {
		exportBtn.addEventListener("click", (e) => {
			e.stopPropagation();
			exportMenu.style.display = exportMenu.style.display === "block" ? "none" : "block";
		});

		document.addEventListener("click", (e) => {
			if (!e.target.closest("#export-dropdown")) {
				exportMenu.style.display = "none";
			}
		});

		const auditLink = document.getElementById("export-audit-link");
		if (auditLink) {
			auditLink.addEventListener("click", (e) => {
				e.preventDefault();
				exportMenu.style.display = "none";
				downloadExport("export/audit", "audit.jsonl");
			});
		}

		const stateLink = document.getElementById("export-state-link");
		if (stateLink) {
			stateLink.addEventListener("click", (e) => {
				e.preventDefault();
				exportMenu.style.display = "none";
				downloadExport("export/state", "state.json");
			});
		}

		const reviewsLink = document.getElementById("export-reviews-link");
		if (reviewsLink) {
			reviewsLink.addEventListener("click", (e) => {
				e.preventDefault();
				exportMenu.style.display = "none";
				downloadExport("export/reviews", "reviews.json");
			});
		}
	}
});
