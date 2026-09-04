functions{
	
	vector cross(vector a, vector b){
		/*Return the cross product of vectors a and b*/

		vector[3] output;

		output[1] = a[2] * b[3] - a[3] * b[2];
		output[2] = a[3] * b[1] - a[1] * b[3];
		output[3] = a[1] * b[2] - a[2] * b[1];
	    
	    return output;

	}

	
	vector rotate_rodrig(vector v, vector k){
		/*Rotate vector v around vector k.
		  The length of k encodes the magnitude of the rotation*/

		real theta;

		theta = sqrt(dot_product(k,k));
		return v * cos(theta) + cross(k,v) * sin(theta) + k * dot_product(k, v) * (1-cos(theta));

	}

	vector mm2pixel(vector p, vector size, vector resolution){
		/*Convert from mm to screen coordinates*/
		vector[3] output;

		output[1] = p[1] * resolution[1] / size[1] + resolution[1] / 2;
		output[2] = p[2] * resolution[2] / size[2] + resolution[2] / 2;
		output[3] = 1;

		return output;
	}	

	vector distortion(vector p, real k1, real k2, real cx, real cy){

		real r;
		real radial;

		vector[3] output;

		output[3] = 1;

		r = (p[1] - cx)^2 + (p[2] - cy)^2;

		radial = k1 * r + k2 * r^2;

		output[1] = p[1] + (p[1] - cx) * radial;
		output[2] = p[2] + (p[2] - cy) * radial;

		return output;

	}

}



data{

	int P; //Number of images
	int K; //Number of corners per image

	real images[P*K*2]; //Image data in homogenous coordiantes
	vector[3] chessboard[K]; //Kx3 chessboard points homogenous
	vector[2] size_;
	vector[2] resolution;
}



parameters{
		
	real<lower = 0, upper = pi()/2> sigma_unif;	
	real fx_raw;
	real fy_raw;
	real cx_raw;
	real cy_raw;

	vector[P] r1_raw;
	vector[P] r2_raw;
	vector<lower = 0>[P] r3_raw;

	vector[P] t1_raw;
	vector[P] t2_raw;
	vector<lower = 0>[P] t3_raw;

	real k1_raw;
	real k2_raw;

	//vector[3] rotations[P]; //Rotations vector (rodriguez for each image)
	//vector[3] translations[P]; //Translation vector for each image
	
}

transformed parameters{
	
	vector[3] rotations[P]; //Rotations vector (rodriguez for each image)
	vector[3] translations[P]; //Translation vector for each image
	
	matrix[3,3] M;	

	real<lower = 0> sigma;

	real<lower = 0> fx;
	real<lower = 0> fy;
	real cx;
	real cy;

	vector[P] r1;
	vector[P] r2;
	vector<lower = 0>[P] r3;

	vector[P] t1;
	vector[P] t2;
	vector<lower = 0>[P] t3;	

	real k1;
	real k2;

	sigma = 0 + 5 * tan(sigma_unif); //implies cauchy(0,5)

	fx = fx_raw * 100 + 1024;
	fy = fy_raw * 100 + 1024;
	cx = cx_raw * 50 + 360;
	cy = cy_raw * 50 + 640;

	r1 = r1_raw * 0.5;
	r2 = r2_raw * 0.5;
	r3 = r3_raw * 1;
	t1 = t1_raw * 50;
	t2 = t2_raw * 50;
	t3 = t3_raw * 300;

	for (img in 1:P){

		rotations[img,1] = r1[img];
		rotations[img,2] = r2[img];
		rotations[img,3] = r3[img];

		translations[img,1] = t1[img];
		translations[img,2] = t2[img];
		translations[img,3] = t3[img];
	}

	M[1,1] = fx;
	M[1,2] = 0;
	M[1,3] = cx;
	M[2,1] = 0;
	M[2,2] = fy;
	M[2,3] = cy;
	M[3,1] = 0.0;
	M[3,2] = 0.0;
	M[3,3] = 1.0;

	k1 = 0 + k1_raw * 0.001;
	k2 = 0 + k2_raw * 0.001;
}


model{
	
	vector[3] Q; 
	vector[3] Q_dist;
	vector[P*K*2] Q_hat;
	int i;
	

	fx_raw ~ normal(0,1);
	fy_raw ~ normal(0,1);
	cy_raw ~ normal(0,1);
	cx_raw ~ normal(0,1);

	r1_raw ~ normal(0,1); 
	r2_raw ~ normal(0,1); 
	r3_raw ~ normal(0,1); 

	t1_raw ~ normal(0,1); 
	t2_raw ~ normal(0,1); 
	t3_raw ~ normal(0,1); 

	k1_raw ~ normal(0, 1);
	k2_raw ~ normal(0, 1);

	i = 1;

	for (img in 1:P){
		
		for (pt in 1:K){

			Q = M * (rotate_rodrig(chessboard[pt], rotations[img]) + translations[img]);		
			Q = Q / Q[3]; //Divide through by w. 

			Q_dist = distortion(Q, k1, k2, resolution[1]/2, resolution[2]/2); //Distort image
			Q_hat[i:i+1] = Q_dist[1:2]; 	
			i = i + 2;					
		}	


	}

	images ~ normal(Q_hat, sigma);
	
}

