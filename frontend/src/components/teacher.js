import { ref } from 'vue'

const teachers = [
  { id: 'zhang', label: '张老师' },
  { id: 'li', label: '李老师' },
  { id: 'wang', label: '王老师' },
]

const currentTeacher = ref(localStorage.getItem('teacher') || 'zhang')

function setTeacher(id) {
  currentTeacher.value = id
  localStorage.setItem('teacher', id)
}

export { teachers, currentTeacher, setTeacher }
