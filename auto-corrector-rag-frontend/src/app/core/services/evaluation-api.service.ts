import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { EvaluationRequest, EvaluationResponse } from '../models/evaluation.model';

@Injectable({ providedIn: 'root' })
export class EvaluationApiService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiBaseUrl}/api/evaluate`;

  evaluate(body: EvaluationRequest): Observable<EvaluationResponse> {
    return this.http.post<EvaluationResponse>(this.base, body);
  }
}
