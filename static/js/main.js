/* Shared progressive enhancements for uploads, booking slots, and demo payments. */
document.addEventListener('DOMContentLoaded', () => {
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
  document.querySelectorAll('form[method="post" i]').forEach(form => {
    if (!form.querySelector('input[name="csrf_token"]') && csrfToken) {
      const input = document.createElement('input'); input.type = 'hidden';
      input.name = 'csrf_token'; input.value = csrfToken; form.prepend(input);
    }
  });
  const reportFile = document.querySelector('#reportFile');
  if (reportFile) reportFile.addEventListener('change', () => {
    document.querySelector('#reportFileName').textContent = reportFile.files[0]?.name || '';
  });

  const photoFile = document.querySelector('#photoFile');
  if (photoFile) photoFile.addEventListener('change', () => {
    const file = photoFile.files[0];
    if (!file) return;
    const preview = document.querySelector('#photoPreview');
    preview.src = URL.createObjectURL(file); preview.style.display = 'block';
    document.querySelector('#photoPreviewWrap').style.display = 'none';
  });

  document.querySelectorAll('.upload-zone').forEach(zone => {
    ['dragenter','dragover'].forEach(name => zone.addEventListener(name, e => { e.preventDefault(); zone.classList.add('dragging'); }));
    ['dragleave','drop'].forEach(name => zone.addEventListener(name, e => { e.preventDefault(); zone.classList.remove('dragging'); }));
  });

  const hospital = document.querySelector('#hospitalSelect');
  const doctor = document.querySelector('#doctorSelect');
  const date = document.querySelector('#appointmentDate');
  const slot = document.querySelector('#slotSelect');
  const amount = document.querySelector('#paymentAmount');

  async function loadDoctors() {
    if (!hospital || !doctor || !hospital.value) return;
    const selected = doctor.dataset.selected || doctor.value;
    try {
      const response = await fetch(`/api/doctors-by-hospital/${hospital.value}`);
      const doctors = await response.json();
      doctor.innerHTML = '<option value="">Choose doctor</option>' + doctors.map(d =>
        `<option value="${d.id}" data-fee="${d.consultation_fee}">${d.name} · ${d.specialty}</option>`).join('');
      if (selected) doctor.value = selected;
      doctor.dataset.selected = '';
      updateFee(); loadSlots();
    } catch (_) { /* Standard form behavior remains available. */ }
  }
  function updateFee() {
    if (!doctor || !amount) return;
    const option = doctor.options[doctor.selectedIndex];
    amount.value = option?.dataset.fee || '';
  }
  async function loadSlots() {
    if (!slot || !hospital?.value || !doctor?.value || !date?.value) return;
    slot.innerHTML = '<option value="">Loading availability…</option>';
    try {
      const response = await fetch(`/api/check-slots?hospital_id=${hospital.value}&doctor_id=${doctor.value}&date=${date.value}`);
      const data = await response.json();
      slot.innerHTML = '<option value="">Choose available time</option>' + data.slots.map(s =>
        `<option value="${s.time}" ${s.full ? 'disabled' : ''}>${s.time} — ${s.label}</option>`).join('');
      const hint = document.querySelector('#slotHint');
      if (hint) hint.innerHTML = '<small class="text-muted"><i class="bi bi-info-circle me-1"></i>Empty means all 3 places remain; full options are disabled.</small>';
    } catch (_) { slot.innerHTML = '<option value="">Could not load slots</option>'; }
  }
  if (hospital && doctor) { hospital.addEventListener('change', loadDoctors); if (hospital.value) loadDoctors(); }
  doctor?.addEventListener('change', () => { updateFee(); loadSlots(); });
  date?.addEventListener('change', loadSlots);

  const paymentMethod = document.querySelector('#paymentMethod');
  function toggleTransaction() {
    if (!paymentMethod) return;
    const digital = paymentMethod.value !== 'Cash at hospital';
    const wrap = document.querySelector('#transactionWrap');
    const input = document.querySelector('#transactionId');
    wrap?.classList.toggle('d-none', !digital);
    if (input) input.required = digital;
    const badge = document.querySelector('#paymentBadge');
    if (badge) { badge.textContent = digital ? 'Paid (demo)' : 'Pending'; badge.className = `badge ${digital ? 'text-bg-success' : 'text-bg-warning'}`; }
  }
  paymentMethod?.addEventListener('change', toggleTransaction); toggleTransaction();

  const chatBody = document.querySelector('.chat-body');
  if (chatBody) chatBody.scrollTop = chatBody.scrollHeight;
});
