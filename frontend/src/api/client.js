import axios from 'axios'

// Instancia axios con baseURL desde variable de entorno
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
})

export default api
