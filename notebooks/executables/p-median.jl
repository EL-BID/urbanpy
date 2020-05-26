using JuMP, GLPK, DelimitedFiles

# Solving the p-median problem by Lagrangian Relaxation
p = 516

# Reading transportation cost data
data = readdlm("../urbanpy/notebooks/dist_matrix_lima.csv", ',');
cc = data[2:end, 1:end];
c = convert(Array{Float64,2}, cc);

aforo = readdlm("../urbanpy/notebooks/aforo.csv", ',');
aa = aforo[2:end];
a = convert(Array{Float64}, aa);

# Reading transportation cost data
demand = readdlm("../urbanpy/notebooks/demand_lima.csv", ',');
dd = demand[2:end];
d = convert(Array{Float64}, dd);

length(d)

size(c)

# the length of 'd' and the number of columns in 'c' must match
@assert length(d) == size(c,2)

locations = 1:size(c,1) # the set, I
customers = 1:length(d) # the set, J
capacity = 1:length(a)

m = Model(GLPK.Optimizer)

@variable(m, x[i in locations, j in customers] >= 0);
@variable(m, y[i in locations], Bin);

@objective(m, Min, sum( d[j]*c[i,j]*x[i,j] for i in locations, j in customers));

@constraint(m, [j in customers], sum( x[i,j] for i in locations) == 1);
@constraint(m, sum( y[i] for i in locations) == p);
@constraint(m, [i in locations, j in customers], x[i,j] <= y[i]);
@constraint(m, [i in aforo], sum(x[i,j] for j in customers) <= a[i]);

JuMP.optimize!(m)

Z_opt = JuMP.objective_value(m);
x_opt = JuMP.value.(x);
y_opt = JuMP.value.(y);

writedlm("optimal_assignments.csv", x_opt)
writedlm("optimal_facilities.csv", y_opt)
