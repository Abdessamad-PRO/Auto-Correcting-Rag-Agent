import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./shared/layout/app-shell.component').then((m) => m.AppShellComponent),
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'workspace' },
      {
        path: 'workspace',
        title: 'Research Workspace · RAG OS',
        loadComponent: () =>
          import('./features/workspace/workspace.page').then((m) => m.WorkspacePage),
      },
      {
        path: 'library',
        title: 'Document Library · RAG OS',
        loadComponent: () =>
          import('./features/library/library.page').then((m) => m.LibraryPage),
      },
      {
        path: 'system',
        title: 'System Health · RAG OS',
        loadComponent: () =>
          import('./features/system-health/system-health.page').then((m) => m.SystemHealthPage),
      },
    ],
  },
  { path: '**', redirectTo: 'workspace' },
];
