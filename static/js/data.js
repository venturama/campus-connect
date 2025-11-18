// list of available courses 
// Used by the course search feature 
window.COURSES = [
  // course/section
  { id:"CSCI101-A", 
  // department 
    dept:"CSCI", 
  // course title 
    number:101,
  // course title 
    title:"Intro to Programming", 
  // number of credit hours 
    credits:3,
  // prerequisite required 
    prereq:"None", 
  // in-person, Hyrid, or Online 
    modality:"In-person",
  // max number of seats
    max:30, 
  // Instructor 
    instructor:"Dr.Smith", 
  // day(s) and time of class
    when:"Mon/Wed 9:00–10:15", 
  // where 
    location:"Hibbs 120", 
  // seats currently filled
    seatsUsed: 12 },
  { id:"INFO361-01", dept:"INFO", number:361, title:"Systems Analysis & Design", credits:3, prereq:"INFO 202", modality:"Hybrid", max:35, instructor:"Prof.Lee", when:"Tue/Thu 11:00–12:15", location:"Snead 205", seatsUsed: 30 },
  { id:"CSCI245-B", dept:"CSCI", number:245, title:"Data Structures", credits:4, prereq:"CSCI 101", modality:"Online", max:25, instructor:"Dr.Smith", when:"Asynchronous", location:"Canvas", seatsUsed: 22 }
];
