# treb

Treb is a user-friendly deploy system for applications running in the cloud.

## About

There are many tools that use code to define how to build an application ([Pants](https://www.pantsbuild.org/), [Bazel](https://bazel.build/)) or how the infrastructure where the application runs ([Terraform](terraform.io/), [Pulumi](https://www.pulumi.com/)), but there's not way to define how to thses artifact will land on the environemnt.

**treb** aims to solve this gap providing a framework to orchestrate deployments, provide a library of libraries of 
proven best practices (i.e. canary deployments, blue-gree deployments, A/B testing, etc.), and support for the main cloud services.

All it's done using Git to store its state and track any change with no need to deploy any remote agent in order to
simplify your system and your life!

## Documentation

Find the docs at [docs.page/fucina/treb](https://docs.page/fucina/treb).

## Build

![build status](https://github.com/fucina/treb/actions/workflows/pants.yaml/badge.svg)
[![codecov](https://codecov.io/gh/fucina/treb/branch/main/graph/badge.svg?token=J503LNI5X1)](https://codecov.io/gh/fucina/treb)
