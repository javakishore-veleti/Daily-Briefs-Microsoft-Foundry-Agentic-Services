import { Component, inject } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { BRIEF_MENUS } from './briefs';
import { UserStore } from './user-store.service';

@Component({
  selector: 'app-shell',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './shell.component.html',
})
export class ShellComponent {
  private readonly router = inject(Router);
  private readonly store = inject(UserStore);

  readonly menus = BRIEF_MENUS;
  readonly user = this.store.current;

  signOut(): void {
    this.store.clear();
    void this.router.navigateByUrl('/signin');
  }
}
