/** Small progressive-enhancement helpers; server-side validation remains authoritative. */
document.addEventListener('DOMContentLoaded', () => {
  const policySelect = document.getElementById('policy_id');
  const memberSelect = document.getElementById('member_id');
  if (policySelect && memberSelect) {
    const filterMembers = () => {
      const policyId = policySelect.value;
      Array.from(memberSelect.options).forEach(option => {
        if (!option.value) { option.hidden = false; return; }
        option.hidden = Boolean(policyId && option.dataset.policy !== policyId);
        if (option.hidden && option.selected) memberSelect.value = '';
      });
    };
    policySelect.addEventListener('input', filterMembers);
    filterMembers();
  }
  const admission = document.querySelector('[name="admission_date"]');
  const discharge = document.querySelector('[name="discharge_date"]');
  if (admission && discharge) {
    admission.addEventListener('change', () => {
      discharge.min = admission.value;
      if (discharge.value && discharge.value < admission.value) discharge.value = admission.value;
    });
  }
});

// Admin account form: hospital desk accounts must be linked to a hospital.
document.addEventListener('DOMContentLoaded', () => {
  const roleSelect = document.getElementById('role');
  const hospitalField = document.getElementById('hospital-field');
  const hospitalSelect = document.getElementById('hospital_id');
  const updateHospitalField = () => {
    if (!roleSelect || !hospitalField || !hospitalSelect) return;
    const needsHospital = roleSelect.value === 'hospital';
    hospitalField.hidden = !needsHospital;
    hospitalSelect.required = needsHospital;
    if (!needsHospital) hospitalSelect.value = '';
  };
  if (roleSelect) {
    roleSelect.addEventListener('change', updateHospitalField);
    updateHospitalField();
  }

  const startDate = document.getElementById('start_date');
  const endDate = document.getElementById('end_date');
  if (startDate && endDate) {
    startDate.addEventListener('change', () => {
      endDate.min = startDate.value;
      if (endDate.value && endDate.value < startDate.value) endDate.value = '';
    });
    if (startDate.value) endDate.min = startDate.value;
  }
});
