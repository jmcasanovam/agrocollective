export const paths = {
  home: "/",
  plots: {
    root: "/plots",
    detail: (id: string) => `/plots/${id}`,
  },
  farms: {
    root: "/farms",
    detail: (id: string) => `/farms/${id}`,
  },
} as const;
