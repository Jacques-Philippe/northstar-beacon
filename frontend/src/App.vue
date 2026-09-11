<script setup>
import { onMounted, ref } from "vue";
import { getIncidents, getMonitorUptime, getStatus } from "./api";

const loading = ref(true);
const error = ref(null);
const status = ref(null);
const uptimes = ref({});
const incidents = ref([]);

function formatPercent(value) {
  return `${value.toFixed(2)}%`;
}

function formatTimestamp(value) {
  return value ? new Date(value).toLocaleString() : "—";
}

async function load() {
  loading.value = true;
  error.value = null;
  try {
    const [statusReport, incidentList] = await Promise.all([getStatus(), getIncidents()]);
    status.value = statusReport;
    incidents.value = incidentList
      .sort((a, b) => new Date(b.opened_at) - new Date(a.opened_at))
      .slice(0, 10);
    const entries = await Promise.all(
      statusReport.monitors.map(async (monitor) => [monitor.monitor_id, await getMonitorUptime(monitor.monitor_id)]),
    );
    uptimes.value = Object.fromEntries(entries);
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <main>
    <header>
      <h1>Beacon</h1>
      <button :disabled="loading" @click="load">Refresh</button>
    </header>

    <p v-if="error" class="error">Could not reach the API: {{ error }}</p>
    <p v-else-if="loading">Loading…</p>

    <template v-else-if="status">
      <section>
        <h2>Monitors ({{ status.up }} up / {{ status.down }} down / {{ status.unknown }} unknown)</h2>
        <table>
          <thead>
            <tr>
              <th></th>
              <th>Name</th>
              <th>Team</th>
              <th>Uptime (24h)</th>
              <th>Uptime (7d)</th>
              <th>Down since</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="monitor in status.monitors" :key="monitor.monitor_id">
              <td><span class="dot" :class="monitor.status"></span></td>
              <td>{{ monitor.name }}</td>
              <td>{{ monitor.owning_team ?? "—" }}</td>
              <td>{{ uptimes[monitor.monitor_id] ? formatPercent(uptimes[monitor.monitor_id].day.uptime_percent) : "—" }}</td>
              <td>{{ uptimes[monitor.monitor_id] ? formatPercent(uptimes[monitor.monitor_id].week.uptime_percent) : "—" }}</td>
              <td>{{ formatTimestamp(monitor.open_since) }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section>
        <h2>Recent incidents</h2>
        <p v-if="incidents.length === 0">No incidents recorded.</p>
        <table v-else>
          <thead>
            <tr>
              <th>Monitor</th>
              <th>Opened</th>
              <th>Resolved</th>
              <th>Duration (s)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="incident in incidents" :key="incident.id">
              <td>{{ incident.monitor_id }}</td>
              <td>{{ formatTimestamp(incident.opened_at) }}</td>
              <td>{{ incident.ongoing ? "ongoing" : formatTimestamp(incident.resolved_at) }}</td>
              <td>{{ incident.duration_seconds.toFixed(1) }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </template>
  </main>
</template>

<style scoped>
main {
  font-family: system-ui, sans-serif;
  max-width: 900px;
  margin: 2rem auto;
  padding: 0 1rem;
}

header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 2rem;
}

th,
td {
  text-align: left;
  padding: 0.4rem 0.6rem;
  border-bottom: 1px solid #ddd;
}

.dot {
  display: inline-block;
  width: 0.75rem;
  height: 0.75rem;
  border-radius: 50%;
}

.dot.up {
  background: #2e9e4c;
}

.dot.down {
  background: #d1373f;
}

.dot.unknown {
  background: #9a9a9a;
}

.error {
  color: #d1373f;
}
</style>
