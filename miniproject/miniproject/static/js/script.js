document.addEventListener('DOMContentLoaded', () => {

    // #region agent log
    function agentLog(location, message, data, hypothesisId) {
        fetch('http://127.0.0.1:7242/ingest/336b4a23-05e1-4d49-bc41-961e1cac4ea0', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'db4b31' },
            body: JSON.stringify({
                sessionId: 'db4b31',
                location,
                message,
                data,
                hypothesisId,
                timestamp: Date.now(),
                runId: 'pre-fix'
            })
        }).catch(() => {});
    }
    // #endregion

    // ========= INPUT PAGE LOGIC =========
    const form = document.getElementById('timetableForm');
    const generateBtn = document.getElementById('generateBtn');

    if (form && generateBtn) {
        form.addEventListener('submit', (e) => {
            // Validate at least one selected class
            const classSelects = document.querySelectorAll('select.class-select');
            const hasClass = Array.from(classSelects).some(s => s.value.trim() !== '');
            if (!hasClass) {
                e.preventDefault();
                alert('Please select at least one class.');
                const first = document.querySelector('select.class-select');
                if (first) first.focus();
                return;
            }

            // Validate at least one subject row chosen
            const subjectSelects = document.querySelectorAll('select.subject-select');
            const hasSubjects = Array.from(subjectSelects).some(s => s.value.trim() !== '');
            if (!hasSubjects) {
                e.preventDefault();
                alert('Please add at least one subject row.');
                return;
            }

            // Disable button and show loading text
            const btnText = generateBtn.querySelector('.btn-text');
            if (btnText) btnText.textContent = 'Generating Timetable...';
            generateBtn.disabled = true;
            generateBtn.style.opacity = '0.7';
        });
    }

    // ========= PER-CLASS ROWS =========
    const semesterTypeSelect = document.getElementById('semesterTypeSelect');

    function getSelectedSemesterType() {
        return semesterTypeSelect ? semesterTypeSelect.value : '';
    }

    function updateRowControls(row, classId, context) {
        const subjSelect = row.querySelector('.subject-select');
        const semesterType = getSelectedSemesterType();
        if (subjSelect) {
            let visibleCount = 0;
            let sampleOpts = [];
            Array.from(subjSelect.options).forEach(opt => {
                const optClass = opt.getAttribute('data-class');
                const optSemType = opt.getAttribute('data-semester-type');
                if (!opt.value || !optClass || !classId) {
                    opt.hidden = false;
                } else {
                    opt.hidden = optClass !== classId;
                }
                if (!opt.hidden && opt.value) visibleCount++;
                if (opt.value && sampleOpts.length < 3) {
                    sampleOpts.push({
                        id: opt.value,
                        class: optClass,
                        semType: optSemType,
                        semester: opt.getAttribute('data-semester'),
                        hidden: opt.hidden
                    });
                }
            });
            // #region agent log
            agentLog('script.js:updateRowControls', 'row filter applied', {
                context: context || 'unknown',
                classId,
                semesterType,
                semesterTypeUsedInFilter: false,
                visibleCount,
                sampleOpts
            }, 'H2');
            // #endregion
            if (subjSelect.selectedOptions.length && subjSelect.selectedOptions[0].hidden) {
                subjSelect.value = '';
            }
        }

        const kind = row.querySelector('.kind-select');
        const labSel = row.querySelector('.lab-select');
        if (kind && labSel) {
            const isLab = kind.value === 'Lab';
            labSel.disabled = !isLab;
            if (!isLab) labSel.value = '';
        }
    }

    // #region agent log
    const firstSubjectOpt = document.querySelector('.subject-select option[value]');
    agentLog('script.js:DOMContentLoaded', 'first subject option dataset', {
        hasSemesterType: firstSubjectOpt ? !!firstSubjectOpt.getAttribute('data-semester-type') : false,
        semesterType: firstSubjectOpt ? firstSubjectOpt.getAttribute('data-semester-type') : null,
        semester: firstSubjectOpt ? firstSubjectOpt.getAttribute('data-semester') : null,
        classId: firstSubjectOpt ? firstSubjectOpt.getAttribute('data-class') : null
    }, 'H1');
    // #endregion

    if (semesterTypeSelect) {
        semesterTypeSelect.addEventListener('change', () => {
            const semesterType = getSelectedSemesterType();
            // #region agent log
            agentLog('script.js:semesterTypeChange', 'semester type changed', {
                semesterType,
                rowsUpdated: 0,
                note: 'no handler updates subject dropdowns on semester change'
            }, 'H3');
            // #endregion
        });
    }

    document.querySelectorAll('.class-section').forEach(section => {
        const classSelect = section.querySelector('.class-select');
        const rowsContainer = section.querySelector('.subject-rows');
        const addBtn = section.querySelector('.add-row-btn');
        const sectionNum = section.getAttribute('data-class-section');

        if (classSelect && rowsContainer) {
            // Initialize existing row
            const firstRow = rowsContainer.querySelector('.subject-row');
            if (firstRow) updateRowControls(firstRow, classSelect.value, 'init');

            classSelect.addEventListener('change', () => {
                const classId = classSelect.value;
                const rows = rowsContainer.querySelectorAll('.subject-row');
                // #region agent log
                const firstOnly = document.querySelector(`select[name="class_${sectionNum}_subject[]"]`);
                agentLog('script.js:classChange', 'class changed', {
                    sectionNum,
                    classId,
                    totalRows: rows.length,
                    querySelectorMatches: firstOnly ? 1 : 0,
                    querySelectorAllMatches: rows.length
                }, 'H4');
                // #endregion
                rows.forEach(r => updateRowControls(r, classId, 'classChange'));
            });

            rowsContainer.addEventListener('change', (e) => {
                if (e.target.closest('.kind-select')) {
                    const row = e.target.closest('.subject-row');
                    updateRowControls(row, classSelect.value, 'kindChange');
                }
            });
        }

        if (addBtn && rowsContainer) {
            addBtn.addEventListener('click', () => {
                const templateRow = rowsContainer.querySelector('.subject-row');
                if (!templateRow) return;
                const clone = templateRow.cloneNode(true);
                const templateVisible = Array.from(
                    templateRow.querySelectorAll('.subject-select option')
                ).filter(o => o.value && !o.hidden).length;

                // Clear inputs
                clone.querySelectorAll('select').forEach(s => s.value = '');
                clone.querySelectorAll('input').forEach(i => i.value = '');

                rowsContainer.appendChild(clone);
                const cloneVisible = Array.from(
                    clone.querySelectorAll('.subject-select option')
                ).filter(o => o.value && !o.hidden).length;
                // #region agent log
                agentLog('script.js:addRow', 'row cloned', {
                    sectionNum,
                    templateVisible,
                    cloneVisibleBeforeUpdate: cloneVisible,
                    classId: classSelect ? classSelect.value : ''
                }, 'H5');
                // #endregion
                updateRowControls(clone, classSelect ? classSelect.value : '', 'addRow');
            });
        }

        // Remove row button (event delegation)
        section.addEventListener('click', (e) => {
            const btn = e.target.closest('.remove-row-btn');
            if (!btn) return;
            const row = btn.closest('.subject-row');
            if (!row) return;
            const allRows = section.querySelectorAll('.subject-row');
            if (allRows.length > 1) row.remove();
            else {
                row.querySelectorAll('select').forEach(s => s.value = '');
                row.querySelectorAll('input').forEach(i => i.value = '');
                updateRowControls(row, classSelect ? classSelect.value : '', 'removeRow');
            }
        });
    });

    // ========= RESERVED SLOTS LOGIC =========
    const addSlotBtn = document.getElementById('addSlotBtn');
    const reservedContainer = document.getElementById('reservedContainer');

    if (addSlotBtn && reservedContainer) {
        addSlotBtn.addEventListener('click', () => {
            const row = document.createElement('div');
            row.className = 'input-grid reserved-row';
            row.style.marginBottom = '0.75rem';
            row.innerHTML = `
                <div class="input-group">
                    <select name="reserved_class" class="form-select">
                        <option value="">All classes</option>
                        ${Array.from(document.querySelectorAll('select.class-select option'))
                            .filter(o => o.value)
                            .map(o => `<option value="${o.value}">${o.textContent}</option>`)
                            .join('')}
                    </select>
                </div>
                <div class="input-group">
                    <select name="reserved_day" class="form-select">
                        <option value="">Select Day...</option>
                        <option value="1">Monday</option>
                        <option value="2">Tuesday</option>
                        <option value="3">Wednesday</option>
                        <option value="4">Thursday</option>
                        <option value="5">Friday</option>
                    </select>
                </div>
                <div class="input-group">
                    <div style="display: flex; gap: 0.5rem; align-items: flex-end;">
                        <select name="reserved_hour" class="form-select" style="flex: 1;">
                            <option value="">Select Hour...</option>
                            <option value="1">Hour 1</option>
                            <option value="2">Hour 2</option>
                            <option value="3">Hour 3</option>
                            <option value="4">Hour 4</option>
                            <option value="5">Hour 5</option>
                            <option value="6">Hour 6</option>
                        </select>
                        <button type="button" class="btn-outline remove-slot-btn" style="padding: 0.75rem 1rem; color: var(--reserved-text); border-color: var(--reserved-text);" title="Remove Slot">🗑️</button>
                    </div>
                </div>
            `;
            reservedContainer.appendChild(row);
        });

        // Use event delegation for dynamically added remove buttons
        reservedContainer.addEventListener('click', (e) => {
            if (e.target.closest('.remove-slot-btn')) {
                const row = e.target.closest('.reserved-row');
                if (reservedContainer.children.length > 1) {
                    row.remove();
                } else {
                    // If it's the last row, just clear the values instead of removing it
                    const selects = row.querySelectorAll('select');
                    selects.forEach(s => s.value = '');
                }
            }
        });
    }

    // ========= RESULT PAGE LOGIC =========
    // Animate timetable cards on load
    const cards = document.querySelectorAll('.timetable-card');
    cards.forEach((card, i) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = `opacity 0.4s ease ${i * 0.1}s, transform 0.4s ease ${i * 0.1}s`;
        requestAnimationFrame(() => {
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        });
    });

    // Hover highlight for subject cells
    const subjectCells = document.querySelectorAll('.td-subject, .td-lab');
    subjectCells.forEach(cell => {
        cell.addEventListener('mouseenter', () => {
            cell.style.transform = 'scale(1.05)';
            cell.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
            cell.style.transition = 'all 0.15s ease';
        });
        cell.addEventListener('mouseleave', () => {
            cell.style.transform = 'scale(1)';
            cell.style.boxShadow = 'none';
        });
    });

    // Animate form inputs on load
    const inputs = document.querySelectorAll('.card');
    inputs.forEach((el, i) => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(15px)';
        el.style.transition = `opacity 0.4s ease ${i * 0.1 + 0.1}s, transform 0.4s ease ${i * 0.1 + 0.1}s`;
        requestAnimationFrame(() => {
            el.style.opacity = '1';
            el.style.transform = 'translateY(0)';
        });
    });
});
