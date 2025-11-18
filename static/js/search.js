
(function(){
  const $ = (sel)=>document.querySelector(sel);
  const resultsBox = $('#resultsBox'); // the entire results section
  const tbody = $('#results'); // <tbody> where course rows go
  const qDept = $('#qDept'); // department
  const qNum = $('#qNum'); // course number
  const qInstr = $('#qInstr'); // instructor
  const info = $('#info'); //status 

  // Hide results and clear any previous output
  // Called on initial load and when Reset is clicked
  function hideResults(){
    if(resultsBox) resultsBox.style.display = 'none';
    if(info) info.textContent = '—';
    if(tbody) tbody.innerHTML = '';
  }
// Show results  (used after a search)
  function showResults(){
    if(resultsBox) resultsBox.style.display = 'block';
  }
// Render an array of course objects as table rows
//Details button per row (toggle)
  function render(rows){
    tbody.innerHTML = '';
    // No matches ->insert a single “no results” 
    if(rows.length === 0){
      const tr = document.createElement('tr');
      tr.innerHTML = '<td colspan="7" class="muted">No matching courses.</td>';
      tbody.appendChild(tr);
      info.textContent = '0 results';
      return;
    }
    // build a row for each course result 
    rows.forEach(c=>{
      const tr = document.createElement('tr');
      tr.setAttribute('data-course-id', c.id);
      const seats = `${c.seatsUsed}/${c.max}`;
      tr.innerHTML = `
        <td>${c.dept}</td>
        <td>${c.number}</td>
        <td>${c.title}</td>
        <td>${c.instructor}</td>
        <td>${c.credits}</td>
        <td>${seats}</td>
        <td><div style="display:flex;gap:6px;flex-wrap:wrap;"><button class="btn-blue" data-id="${c.id}" style="padding:6px 10px;" data-act="details">Details</button><form method="post" action="/register/${c.id}" onsubmit="return confirm('Register for ${c.dept} ${c.number}?')"><button type="submit" class="btn-blue" style="padding:6px 10px;background:#16a34a;border:none;">Register</button></form></div></td>
      `;
      tbody.appendChild(tr);
    });
    info.textContent = rows.length + ' result' + (rows.length!==1?'s':'');
//Attach click Details button
    tbody.querySelectorAll('button[data-id]').forEach(btn=>{
      // Pass both the course id and the actual button element to the toggle
      btn.addEventListener('click', ()=>{ if(btn.getAttribute('data-act')==='details'){ toggleDetails(btn.getAttribute('data-id'), btn);} });
    });
  }

  // One toggle per course row (multiple can be open)
  function toggleDetails(id, buttonEl){
  // The main row containing the button
    const row = buttonEl.closest('tr');
    // The row immediately after the main row
    const next = row.nextElementSibling;
    // If the next row is a details row for this same course → collapse it
    if(next && next.classList.contains('details-row') && next.getAttribute('data-id') === id){
      next.remove();
      buttonEl.textContent = 'Details';
      return;
    }
    //otherwise open the details panel
    const c = window.COURSES.find(x=>x.id===id);
    if(!c) return;
    // Build a new details row
    const d = document.createElement('tr');
    d.className = 'details-row';
    d.setAttribute('data-id', id);
    const used = c.seatsUsed, max = c.max;
    d.innerHTML = `<td colspan="7">
      <div class="details">
        <strong>${c.dept} ${c.number} – ${c.title}</strong><br>
        Prerequisites: <em>${c.prereq}</em> • Modality: <em>${c.modality}</em><br>
        Time/Place: ${c.when} • ${c.location}<br>
        Seats: <strong>${used}/${max}</strong>
      </div>
    </td>`;
    row.insertAdjacentElement('afterend', d);
    buttonEl.textContent = 'Hide';
  }
  function search(){
  //rules
  // - dept → uppercase (INFO/CSCI)
  // - num  → string compare so partials like “3” work (361 matches)
  // - instr → lowercase for partial, case-insensitive matches
  // search for what the user has typed 
    const dept = qDept.value.trim().toUpperCase();
    const num = qNum.value.trim();
    const instr = qInstr.value.trim().toLowerCase();
    //  only check these if they're not empty 
    const filtered = window.COURSES.filter(c =>
      (!dept || c.dept.includes(dept)) && 
      (!num || String(c.number).includes(num)) &&
      (!instr || c.instructor.toLowerCase().includes(instr))
    );
    showResults(); // show box 
    render(filtered); // show table 
  }
// When Search button is clicked, run search
// When Reset button is clicked, clear everything
  $('#btnSearch').addEventListener('click', search);
  $('#btnReset').addEventListener('click', ()=>{
    qDept.value=''; qNum.value=''; qInstr.value='';
    hideResults(); // hide results until next search
  });

  // At start, hide results 
  hideResults();
})();
