const PORT = process.env.NODE_ENV === 'production' ? 8080 : 8081;

export const apiRoot = `http://localhost:${PORT}/`;
