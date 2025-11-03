(() => {
  const form = document.getElementById('suggestNetForm');
  if (!form) return;

  const recurrenceType = document.getElementById('recurrenceType');
  const weeklyPane = document.getElementById('weeklyRecurrence');
  const monthlyPane = document.getElementById('monthlyRecurrence');
  const weeklyBoxes = weeklyPane ? Array.from(weeklyPane.querySelectorAll('input[type="checkbox"]')) : [];
  const monthlyPosition = document.getElementById('monthlyPosition');
  const monthlyWeekday = document.getElementById('monthlyWeekday');
  const rruleField = document.getElementById('rruleField');
  const statusBox = document.getElementById('submissionStatus');
  const submitButton = form.querySelector('button[type="submit"]');

  const netNameInput = document.getElementById('netName');
  const netDescriptionInput = document.getElementById('netDescription');
  const startTimeInput = document.getElementById('startTime');
  const durationInput = document.getElementById('durationMinutes');
  const contactEmailInput = document.getElementById('contactEmail');
  const additionalInfoInput = document.getElementById('additionalInfo');

  function setStatus(message, type = 'info') {
    if (!statusBox) return;
    statusBox.textContent = message;
    statusBox.className = '';
    statusBox.classList.add('submission-status', `submission-status--${type}`);
  }

  function toggleRecurrencePane() {
    const value = recurrenceType ? recurrenceType.value : 'weekly';
    if (!weeklyPane || !monthlyPane) return;
    if (value === 'monthly') {
      monthlyPane.hidden = false;
      monthlyPane.setAttribute('aria-hidden', 'false');
      weeklyPane.hidden = true;
      weeklyPane.setAttribute('aria-hidden', 'true');
    } else {
      weeklyPane.hidden = false;
      weeklyPane.setAttribute('aria-hidden', 'false');
      monthlyPane.hidden = true;
      monthlyPane.setAttribute('aria-hidden', 'true');
    }
  }

  function buildWeeklyRrule() {
    const selectedDays = weeklyBoxes.filter((box) => box.checked).map((box) => box.value);
    if (!selectedDays.length) {
      throw new Error('Pick at least one weekday for the weekly schedule.');
    }
    return `FREQ=WEEKLY;BYDAY=${selectedDays.join(',')}`;
  }

  function buildMonthlyRrule() {
    const pos = monthlyPosition ? monthlyPosition.value : '1';
    const weekday = monthlyWeekday ? monthlyWeekday.value : 'MO';
    if (!weekday) {
      throw new Error('Choose a weekday for the monthly schedule.');
    }
    return `FREQ=MONTHLY;BYDAY=${weekday};BYSETPOS=${pos}`;
  }

  function buildRrule() {
    const type = recurrenceType ? recurrenceType.value : 'weekly';
    if (type === 'monthly') {
      return buildMonthlyRrule();
    }
    return buildWeeklyRrule();
  }

  function validateEmail(email) {
    return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setStatus('', 'info');

    if (submitButton) {
      submitButton.disabled = true;
    }

    try {
      const name = netNameInput.value.trim();
      const description = netDescriptionInput.value.trim();
      const category = document.getElementById('netCategory').value;
      const startLocal = startTimeInput.value.trim();
      const duration = durationInput.value.trim();
      const timeZone = document.getElementById('timeZone').value;
      const allstar = document.getElementById('allstarNode').value.trim();
      const echolink = document.getElementById('echolinkNode').value.trim();
      const frequency = document.getElementById('hfFrequency').value.trim();
      const mode = document.getElementById('hfMode').value.trim();
      const additionalInfo = additionalInfoInput.value.trim();
      const contactName = document.getElementById('contactName').value.trim();
      const contactEmail = contactEmailInput.value.trim();
      const honeypot = document.getElementById('website').value.trim();

      if (honeypot) {
        setStatus('Submission received.', 'success');
        form.reset();
        toggleRecurrencePane();
        if (submitButton) submitButton.disabled = false;
        return;
      }

      if (!name) throw new Error('Net name is required.');
      if (!description) throw new Error('Please tell us about the net.');
      if (!startLocal) throw new Error('Start time is required.');
      if (!duration || Number(duration) <= 0) throw new Error('Duration must be a positive number.');
      if (!contactEmail || !validateEmail(contactEmail)) throw new Error('Valid contact email is required.');

      const rrule = buildRrule();
      rruleField.value = rrule;

      const payload = {
        name,
        description,
        category,
        start_local: startLocal,
        duration_min: duration,
        time_zone: timeZone,
        rrule,
        allstar,
        echolink,
        frequency,
        mode,
        additional_info: additionalInfo,
        contact_name: contactName,
        contact_email: contactEmail,
        submission_note: additionalInfo || '',
        website: honeypot,
      };

      setStatus('Submitting…', 'info');
      const response = await fetch('/api/public/suggest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (response.status === 202) {
        const data = await response.json();
        setStatus(`Thanks! We saved “${name}” for review. Reference ID: ${data.generated_id}`, 'success');
        form.reset();
        toggleRecurrencePane();
      } else {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || 'Could not submit your net. Please try again.');
      }
    } catch (error) {
      setStatus(error.message, 'error');
    } finally {
      if (submitButton) submitButton.disabled = false;
    }
  }

  toggleRecurrencePane();
  if (recurrenceType) {
    recurrenceType.addEventListener('change', toggleRecurrencePane);
  }
  form.addEventListener('submit', handleSubmit);
})();
